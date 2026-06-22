import logging
from pathlib import Path
from src.map_generator import WorldEngineRunner, WorldConfig
from src.caller import run_pipeline  # Se serve ancora internamente a src.caller, altrimenti usiamo run_pipeline definita sotto

# Configurazione base per visualizzare i log sulla console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def generate_world_map():
    """Fase 1: Generazione della mappa del mondo tramite WorldEngine."""
    logging.info("Inizio generazione della mappa...")
    
    world_cfg = WorldConfig
    world_cfg.WORLD_NAME = "world"
    world_cfg.WIDTH = 1000
    world_cfg.HEIGHT = 500
    world_cfg.NUM_PLATES = 15

    runner = WorldEngineRunner(world_cfg)
    runner.run()
    
    logging.info("Mappa generata con successo.")


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


def run_full_workflow():
    """Funzione di orchestrazione che unisce i due processi."""
    logging.info("=== Avvio Workflow Completo ===")
    
    # 1. Genera la mappa
    generate_world_map()
    
    print("\n" + "="*40 + "\n") # Separatore visivo in console
    
    # 2. Chiama LM Studio
    process_lm_studio_prompts()
    
    logging.info("=== Workflow Completato Con Successo ===")


if __name__ == "__main__":
    # Il main invoca la terza funzione di orchestrazione
    run_full_workflow()