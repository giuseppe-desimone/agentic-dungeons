import logging
from pathlib import Path
from src.map_generator import WorldEngineRunner, WorldConfig
from src.caller import run_pipeline  
from src.poi_engine import POIEngine

# Configurazione base per visualizzare i log sulla console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def process_lm_studio_prompts():
    """Fase 2: Gestione dei prompt ed esecuzione della chiamata a LM Studio."""
    logging.info("Inizio elaborazione prompt con LM Studio...")
    
    # Definizione dinamica dei percorsi dei prompt basata sulla posizione di questo file
    current_dir = Path(__file__).resolve().parent
    system_prompt_path = current_dir / "prompt" / "system_prompt.md"
    input_query_path = current_dir / "prompt" / "input_query.md"

    # Esegue la pipeline importata (dal codice modificato in precedenza)
    # Nota: Assicurati che 'run_pipeline' gestisca correttamente i print/log interni
    try:
        response_message, reasoning = run_pipeline(system_prompt_path, input_query_path)
        
        # Mostra i risultati usando il logger per uniformità
        if reasoning:
            logging.info("\n--- Ragionamento del Modello ---\n%s", reasoning)
            
        logging.info("\n--- Risposta Finale ---\n%s", response_message)
        
    except FileNotFoundError:
        logging.error("Interruzione della pipeline LM Studio a causa di file mancanti.")
    except Exception as e:
        logging.error(f"Errore durante la chiamata a LM Studio: {e}")


def generate_world_map():
    """Fase 1: Generazione della mappa e analisi dei POI tramite Python."""
    logging.info("Inizio generazione della mappa...")
    
    world_cfg = WorldConfig
    world_cfg.WORLD_NAME = "world"
    world_cfg.WIDTH = 1000
    world_cfg.HEIGHT = 500
    world_cfg.NUM_PLATES = 15

    runner = WorldEngineRunner(world_cfg)
    runner.run()
    
    logging.info("Mappa generata con successo. Avvio analisi deterministica dei POI...")
    
    # --- NUOVA PARTE DETERMINISTICA ---
    poi_engine = POIEngine(world_cfg)
    # Chiediamo a Python di trovare i 5 punti migliori sul pianeta distanti almeno 20 pixel l'uno dall'altro
    lista_poi = poi_engine.extract_pois(num_civilizations=5, min_distance_pixels=20)
    
    for i, poi in enumerate(lista_poi):
        logging.info(f"POI #{i+1} trovato alle coordinate (X: {poi['x']}, Y: {poi['y']}) | Bioma: {poi['biome']} | Score: {poi['score']:.2f}")
        
    return lista_poi # Ritorniamo i dati estratti


def run_full_workflow():
    """Funzione di orchestrazione che unisce i due processi."""
    logging.info("=== Avvio Workflow Completo ===")
    
    # 1. Genera la mappa ed estrae i POI via Python
    pois = generate_world_map()
    
    print("\n" + "="*40 + "\n") # Separatore visivo in console
    
    # 2. Passa i POI estratti a LM studio (Fase da implementare successivamente)
    # Ad esempio puoi serializzare i POI in un file md temporaneo o passarli come argomento
    #process_lm_studio_prompts() 

    logging.info("=== Workflow Completato Con Successo ===")
    


if __name__ == "__main__":
    # Il main invoca la terza funzione di orchestrazione
    run_full_workflow()