import os
import sys
import logging
import requests
import h5py
import numpy as np
from typing import TypedDict, Dict, Any, Tuple
from pathlib import Path
from PIL import Image
from langgraph.graph import StateGraph, END

# Importiamo i componenti esistenti del tuo ecosistema
from worldengine.cli.main import main as worldengine_main
from src.map_config import WorldConfig, biome_colors, MAX_CELSIUS, MIN_CELSIUS

logger = logging.getLogger("GameAgent")

# ==========================================
# 1. DEFINIZIONE DELLO STATO DEL GRAFO (SRP)
# ==========================================
class GameAgentState(TypedDict):
    """Definisce il contratto di stato che attraversa l'intero grafo."""
    # Input iniziali
    x: int
    y: int
    world_name: str
    output_dir: str
    
    # Dati intermedi generati dai nodi
    environmental_data: Dict[str, Any]
    input_query: str
    system_prompt: str
    
    # Output finali
    response_message: str
    reasoning: str


# ==========================================
# 2. SERVIZI ISOLATI (SOLID - Single Responsibility)
# ==========================================

class WorldGenerationService:
    """Gestisce esclusivamente la computazione algoritmica e la scrittura del file HDF5."""
    
    def __init__(self, config: WorldConfig):
        self.cfg = config

    def generate_world(self) -> bool:
        """Esegue WorldEngine iniettando i parametri di configurazione."""
        args_list = self._build_arguments()
        original_argv = sys.argv
        success = False
        try:
            sys.argv = ["worldengine_script"] + args_list
            worldengine_main()
            success = True
        except SystemExit as e:
            if e.code in [0, None]:
                success = True
        except Exception as e:
            logger.error(f"Errore critico durante la generazione del mondo: {e}", exc_info=True)
        finally:
            sys.argv = original_argv
            
        if success:
            self._post_processing_injection()
        return success

    def _build_arguments(self) -> list:
        c = self.cfg
        params = [c.OPERATOR]
        if c.OUTPUT_DIR: params.extend(["--output-dir", c.OUTPUT_DIR])
        if c.WORLD_NAME: params.extend(["--worldname", c.WORLD_NAME])
        if c.USE_HDF5: params.append("--hdf5")
        if c.SEED is not None: params.extend(["--seed", str(c.SEED)])
        if c.STEP: params.extend(["--step", c.STEP])
        if c.WIDTH: params.extend(["--width", str(c.WIDTH)])
        if c.HEIGHT: params.extend(["--height", str(c.HEIGHT)])
        if c.NUM_PLATES: params.extend(["--number-of-plates", str(c.NUM_PLATES)])
        if c.VERBOSE: params.append("--verbose")
        if c.GENERATE_RIVERS: params.append("--rivers")
        if c.GENERATE_SATELLITE: params.append("--sat")
        if c.GENERATE_ICE: params.append("--ice")
        if c.NOT_FADE_BORDERS: params.append("--not-fade-borders")
        return params

    def _post_processing_injection(self):
        """Calcola e inietta i dataset dimensionali e normalizzati nell'HDF5."""
        widths, areas, sides, tiles_per_row, radius = self._calc_dimensions()
        file_path = os.path.join(self.cfg.OUTPUT_DIR, f"{self.cfg.WORLD_NAME}.world")
        
        with h5py.File(file_path, 'r+') as f:
            # Iniezione dati dimensionali
            dim_grp = f.require_group("dimensional_data")
            dim_grp.create_dataset("pixel_area_per_row", data=areas, dtype='int32')
            dim_grp.create_dataset("pixel_sqr_side_per_row", data=sides, dtype='int32')
            dim_grp.create_dataset("pixel_width_per_row", data=widths, dtype='int32')
            dim_grp.create_dataset("valid_tiles_per_row", data=tiles_per_row, dtype='int32')
            
            # Iniezione dati normalizzati
            norm_grp = f.require_group('normalized_data')
            
            if 'elevation/data' in f:
                norm_grp.create_dataset('elevation_meters', 
                                        data=self._scale_elevation(f['elevation/data'][:], f['elevation/thresholds/sea'][()], f['elevation/thresholds/plain'][()], f['elevation/thresholds/hill'][()]), 
                                        dtype='int32')
            if 'humidity/data' in f:
                hd = f['humidity/data'][:]
                norm_grp.create_dataset('humidity_percentage', data=np.round(np.clip((hd - np.min(hd)) / (np.max(hd) - np.min(hd) or 1) * 100, 0, 100)).astype(np.int32))
            if 'watermap/data' in f:
                wd = f['watermap/data'][:]
                norm_grp.create_dataset('surface_runoff_mm', data=np.round((wd / (np.max(wd) or 1)) * 2000).astype(np.int32))
            if 'river_map' in f:
                rd = f['river_map'][:]
                norm_grp.create_dataset('river_flow_m3s', data=np.round((rd / (np.max(rd) or 1)) * 6500).astype(np.int32))
            if 'precipitation/data' in f:
                pd = f['precipitation/data'][:]
                norm_grp.create_dataset('precipitation_mm', data=np.round(np.interp(pd, [np.min(pd), f['precipitation/thresholds/low'][()], f['precipitation/thresholds/med'][()], np.max(pd)], [0.0, 250.0, 1000.0, 4000.0])).astype(np.int32))
            if 'temperature/data' in f:
                td = f['temperature/data'][:]
                norm_grp.create_dataset('temperature_celsius', data=np.round(MIN_CELSIUS + ((td - np.min(td)) / (np.max(td) - np.min(td) or 1)) * (MAX_CELSIUS - MIN_CELSIUS)).astype(np.int32))
            
            # Iniezione nomi biomi dall'immagine generata
            biome_img_path = os.path.join(self.cfg.OUTPUT_DIR, f"{self.cfg.WORLD_NAME}_biome.png")
            if os.path.exists(biome_img_path):
                with Image.open(biome_img_path) as img:
                    img_arr = np.array(img.convert('RGB'))
                biome_names = np.full((self.cfg.HEIGHT, self.cfg.WIDTH), "ocean", dtype=object)
                for name, color in biome_colors.items():
                    mask = np.all(img_arr == np.array(color), axis=-1)
                    if np.any(mask): biome_names[mask] = name
                dt = h5py.special_dtype(vlen=str)
                norm_grp.create_dataset('biome_names', data=biome_names, dtype=dt)

    def _calc_dimensions(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
        r, c, rad = self.cfg.HEIGHT, self.cfg.WIDTH, 6371000
        p_height = (np.pi * rad) / r
        lats = np.radians(np.linspace(90 - (180.0 / r / 2), -90 + (180.0 / r / 2), r))
        p_widths = (2 * np.pi * rad * np.cos(lats)) / c
        areas = p_widths * p_height
        return np.round(p_widths).astype(np.int32), np.round(areas).astype(np.int32), np.round(np.sqrt(np.maximum(areas, 0))).astype(np.int32), np.maximum(np.round(c * np.cos(lats)).astype(np.int32), 1), rad

    def _scale_elevation(self, data, sea, plain, hill):
        res = np.zeros_like(data, dtype=np.float32)
        m_lower = data <= plain
        res[m_lower] = (data[m_lower] - sea) * (300.0 / (plain - sea or 1))
        m_upper = data > plain
        res[m_upper] = 300.0 + (data[m_upper] - plain) * (300.0 / (hill - plain or 1))
        return np.round(res).astype(np.int32)


class MapRetrieverService:
    """Classe focalizzata sull'estrazione dei dati geografici e sulla validazione dei confini."""
    
    @staticmethod
    def extract_environmental_data(file_path: str, x: int, y: int) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Mappa HDF5 non trovata al percorso: {file_path}")

        mapping = {
            "Elevation": ("elevation_meters", "m"),
            "Humidity": ("humidity_percentage", "%"),
            "Watermap": ("surface_runoff_mm", "mm/anno"),
            "River map": ("river_flow_m3s", "m³/s"),
            "Precipitation": ("precipitation_mm", "mm/anno"),
            "Temperature": ("temperature_celsius", "°C"),
            "Biomes": ("biome_names", "")
        }

        extracted_data = {}
        with h5py.File(file_path, 'r') as f:
            if 'normalized_data' not in f:
                raise KeyError("Il file HDF5 non contiene la struttura 'normalized_data' normalizzata.")
            
            group = f['normalized_data']
            
            # Controllo dinamico dei limiti della matrice
            any_key = list(mapping.values())[0][0]
            max_y, max_x = group[any_key].shape
            
            if not (0 <= x < max_x and 0 <= y < max_y):
                raise IndexError(f"Coordinate ({x}, {y}) fuori matrice. Max consentito: X={max_x - 1}, Y={max_y - 1}")

            for label, (key, unit) in mapping.items():
                if key in group:
                    val = group[key][y, x] # Indicizzazione HDF5 standard [Riga, Colonna]
                    if isinstance(val, bytes):
                        val = val.decode('utf-8')
                    extracted_data[label] = f"{val} {unit}".strip()
                else:
                    extracted_data[label] = "n/d"
                    
        return extracted_data


# ==========================================
# 3. NODI DEL GRAFO (LangGraph Nodes)
# ==========================================

def world_generation_node(state: GameAgentState) -> GameAgentState:
    """Nodo 1: Genera il mondo se non è già presente sul disco."""
    logger.info("[Nodo 1] Verifica e Generazione del Mondo...")
    
    # Prepariamo la configurazione iniettando le variabili di stato
    config = WorldConfig
    config.WORLD_NAME = state.get("world_name", "test")
    config.OUTPUT_DIR = state.get("output_dir", "assets/map")
    
    target_file = os.path.join(config.OUTPUT_DIR, f"{config.WORLD_NAME}.world")
    
    if not os.path.exists(target_file):
        logger.info(f"File {target_file} non trovato. Avvio generazione procedurale...")
        generator = WorldGenerationService(config)
        generator.generate_world()
    else:
        logger.info(f"Mappa esistente rilevata in {target_file}. Generazione saltata (Ottimizzazione Cache).")
        
    return state


def map_retriever_node(state: GameAgentState) -> GameAgentState:
    """Nodo 2: Prende le coordinate in input e recupera i dati ambientali specifici."""
    logger.info(f"[Nodo 2] Estrazione dati alle coordinate X: {state['x']}, Y: {state['y']}")
    
    file_path = os.path.join(state["output_dir"], f"{state['world_name']}.world")
    env_data = MapRetrieverService.extract_environmental_data(file_path, state["x"], state["y"])
    
    # Prepariamo la stringa formattata da passare al prompt
    query_buffer = ["Generate a fantasy landscape description based on the following environmental data:\n\n[ENVIRONMENTAL DATA]"]
    for label, val in env_data.items():
        query_buffer.append(f"{label:<15} : {val}")
    input_query = "\n".join(query_buffer)
    
    return {
        **state,
        "environmental_data": env_data,
        "input_query": input_query
    }


def description_generator_node(state: GameAgentState) -> GameAgentState:
    """Nodo 3: Genera la descrizione narrativa interfacciandosi con il LLM locale."""
    logger.info("[Nodo 3] Richiesta di generazione narrativa inviata a LM Studio...")
    
    url = "http://localhost:1234/api/v1/chat"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "model": "google/gemma-4-12b",
        "system_prompt": state["system_prompt"],
        "input": state["input_query"],
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        message_content = ""
        reasoning_content = ""
        
        for output in data.get("output", []):
            if output.get("type") == "message":
                message_content = output.get("content")
            elif output.get("type") == "reasoning":
                reasoning_content = output.get("content")
                
        return {
            **state,
            "response_message": message_content,
            "reasoning": reasoning_content
        }
    except Exception as e:
        error_msg = f"Errore di comunicazione con LM Studio: {e}"
        logger.error(error_msg)
        return {**state, "response_message": error_msg}


# ==========================================
# 4. COMPILAZIONE E MONTAGGIO DEL GRAFO
# ==========================================
workflow = StateGraph(GameAgentState)

# Aggiunta nodi
workflow.add_node("generation_stage", world_generation_node)
workflow.add_node("retrieval_stage", map_retriever_node)
workflow.add_node("narrative_stage", description_generator_node)

# Configurazione del percorso sequenziale logico
workflow.set_entry_point("generation_stage")
workflow.add_edge("generation_stage", "retrieval_stage")
workflow.add_edge("retrieval_stage", "narrative_stage")
workflow.add_edge("narrative_stage", END)

# Esportazione dell'applicazione del grafo pronto
game_agent_app = workflow.compile()


# ==========================================
# 5. ENTRYPOINT DI ESECUZIONE (Main)
# ==========================================
def run_game_agent_pipeline(x: int, y: int, world_name: str = "test"):
    """Inizializza ed esegue l'intera pipeline agentica."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Risoluzione dinamica dei prompt
    current_dir = Path(__file__).resolve().parent
    sys_prompt_path = current_dir / "src" / "basic_agent" / "prompt" / "system_prompt.md"
    
    # Fallback inline del system prompt se il file non esiste
    if sys_prompt_path.exists():
        system_prompt = sys_prompt_path.read_text(encoding="utf-8")
    else:
        system_prompt = (
            "You are an expert fantasy worldbuilder. Translate raw data into an immersive "
            "and atmospheric single-paragraph description in Italian. Conclude with a brief atmospheric hook."
        )

    # Definizione dello stato di partenza (Input utente / Motore di gioco)
    initial_state: GameAgentState = {
        "x": x,
        "y": y,
        "world_name": world_name,
        "output_dir": "assets/map",
        "environmental_data": {},
        "input_query": "",
        "system_prompt": system_prompt,
        "response_message": "",
        "reasoning": ""
    }

    logger.info(f"=== ESECUZIONE PIPELINE AGENTICA PER IL MONDO: {world_name} ===")
    final_state = game_agent_app.invoke(initial_state)
    
    print("\n" + "="*50)
    print(f"RISULTATO GENERAZIONE LOCALE (Coordinate: X={x}, Y={y})")
    print("="*50)
    if final_state.get("reasoning"):
        print(f"\n🧠 PENSIERO DELL'AGENTE:\n{final_state['reasoning']}")
    print(f"\n🗺️ DESCRIZIONE AMBIENTALE:\n{final_state['response_message']}\n")


if __name__ == "__main__":
    # Esegui il test simulando l'esplorazione sulla coordinata X: 450, Y: 200
    run_game_agent_pipeline(x=450, y=200, world_name="test")