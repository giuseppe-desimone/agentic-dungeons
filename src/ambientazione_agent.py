import base64
import requests
from pathlib import Path
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END

# 1. Definizione dello Stato del Grafo
class WorldBuildingState(TypedDict):
    planisfero_path: Path
    prompts_dir: Path
    world_bible: str
    capitolo_1: str
    capitolo_2: str
    capitolo_3: str
    capitolo_4: str
    output_finale: str

# 2. Funzioni di utilità per file e immagini
def read_file(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Errore: File non trovato in {file_path}")
        return ""

def encode_image_to_base64(image_path: Path) -> str:
    """Codifica l'immagine in base64 per i modelli Vision."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def call_lm_studio_vision(system_prompt: str, user_prompt: str, image_path: Path) -> str:
    """Chiamata a LM Studio che include un'immagine (Fase 1)."""
    url = "http://localhost:1234/v1/chat/completions" # Endpoint standard OpenAI di LM Studio
    
    base64_image = encode_image_to_base64(image_path)
    
    payload = {
        "model": "google/gemma-4-12b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }
        ],
        "temperature": 0.7
    }
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def call_lm_studio_text(system_prompt: str, user_prompt: str) -> str:
    """Chiamata standard di solo testo per i singoli capitoli (Fase 2)."""
    url = "http://localhost:1234/v1/chat/completions"
    
    payload = {
        "model": "google/gemma-4-12b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7
    }
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# 3. Nodi del Grafo (I passaggi dell'Agente)

def genera_world_bible(state: WorldBuildingState) -> dict:
    print("\n--- Generazione della Bibbia del Mondo (Analisi Mappa) ---")
    sys_p = read_file(state["prompts_dir"] / "fase1_system.md")
    user_p = read_file(state["prompts_dir"] / "fase1_user.md")
    
    # Inserisci le idee di partenza se necessario (oppure lasciale già scritte nel file md)
    risposta = call_lm_studio_vision(sys_p, user_p, state["planisfero_path"])
    return {"world_bible": risposta}

def genera_capitolo_1(state: WorldBuildingState) -> dict:
    print("\n--- Generazione Capitolo 1: Geografia ---")
    sys_p = read_file(state["prompts_dir"] / "cap1_system.md")
    user_p = read_file(state["prompts_dir"] / "cap1_user.md")
    
    # Inietta la Bibbia del mondo generata nel segnaposto del prompt
    user_p = user_p.replace("[INCOLLA QUI L'OUTPUT GENERATO NELLA FASE 1]", state["world_bible"])
    
    risposta = call_lm_studio_text(sys_p, user_p)
    return {"capitolo_1": risposta}

def genera_capitolo_2(state: WorldBuildingState) -> dict:
    print("\n--- Generazione Capitolo 2: Popoli e Culture ---")
    sys_p = read_file(state["prompts_dir"] / "cap2_system.md")
    user_p = read_file(state["prompts_dir"] / "cap2_user.md")
    
    user_p = user_p.replace("[INCOLLA QUI L'OUTPUT GENERATO NELLA FASE 1]", state["world_bible"])
    
    risposta = call_lm_studio_text(sys_p, user_p)
    return {"capitolo_2": risposta}

def genera_capitolo_3(state: WorldBuildingState) -> dict:
    print("\n--- Generazione Capitolo 3: Magia ---")
    sys_p = read_file(state["prompts_dir"] / "cap3_system.md")
    user_p = read_file(state["prompts_dir"] / "cap3_user.md")
    
    user_p = user_p.replace("[INCOLLA QUI L'OUTPUT GENERATO NELLA FASE 1]", state["world_bible"])
    
    risposta = call_lm_studio_text(sys_p, user_p)
    return {"capitolo_3": risposta}

def genera_capitolo_4(state: WorldBuildingState) -> dict:
    print("\n--- Generazione Capitolo 4: Fazioni e Fedi ---")
    sys_p = read_file(state["prompts_dir"] / "cap4_system.md")
    user_p = read_file(state["prompts_dir"] / "cap4_user.md")
    
    user_p = user_p.replace("[INCOLLA QUI L'OUTPUT GENERATO NELLA FASE 1]", state["world_bible"])
    
    risposta = call_lm_studio_text(sys_p, user_p)
    return {"capitolo_4": risposta}

def compila_manuale_finale(state: WorldBuildingState) -> dict:
    print("\n--- Compilazione del Manuale Finale ---")
    # Concatena tutto in un unico grande file Markdown separando con interruzioni di pagina fittizie o linee orizzontali
    separatore = "\n\n---\n\n"
    manuale = (
        f"{state['world_bible']}{separatore}"
        f"{state['capitolo_1']}{separatore}"
        f"{state['capitolo_2']}{separatore}"
        f"{state['capitolo_3']}{separatore}"
        f"{state['capitolo_4']}"
    )
    return {"output_finale": manuale}

# 4. Costruzione del Grafo di LangGraph
def build_graph():
    builder = StateGraph(WorldBuildingState)
    
    # Aggiungi i nodi
    builder.add_node("bible", genera_world_bible)
    builder.add_node("cap1", genera_capitolo_1)
    builder.add_node("cap2", genera_capitolo_2)
    builder.add_node("cap3", genera_capitolo_3)
    builder.add_node("cap4", genera_capitolo_4)
    builder.add_node("compile", compila_manuale_finale)
    
    # Imposta i collegamenti sequenziali (Edge)
    builder.set_entry_point("bible")
    builder.add_edge("bible", "cap1")
    builder.add_edge("cap1", "cap2")
    builder.add_edge("cap2", "cap3")
    builder.add_edge("cap3", "cap4")
    builder.add_edge("cap4", "compile")
    builder.add_edge("compile", END)
    
    return builder.compile()

# 5. Esecuzione
def main():
    current_dir = Path(__file__).resolve().parent
    
    # Configura i percorsi dei tuoi asset
    config_iniziale: WorldBuildingState = {
        "planisfero_path": current_dir / "assets" / "map" / "world_satellite.png",
        "prompts_dir": current_dir / "prompts",
        "world_bible": "",
        "capitolo_1": "",
        "capitolo_2": "",
        "capitolo_3": "",
        "capitolo_4": "",
        "output_finale": ""
    }
    
    # Compila ed esegui il grafo
    grafo = build_graph()
    risultato_finale = grafo.invoke(config_iniziale)
    
    # Salva il manuale completo in un file markdown
    output_path = current_dir / "manuale_ambientazione_completo.md"
    output_path.write_text(risultato_finale["output_finale"], encoding="utf-8")
    
    print(f"\n[SUCCESSO] Il manuale è stato generato e salvato in: {output_path}")

if __name__ == "__main__":
    main()