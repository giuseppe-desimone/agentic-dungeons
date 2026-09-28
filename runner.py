import logging
from src.world.world_generator import WorldEngineRunner, WorldConfig

# Configurazione base per visualizzare i log sulla console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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
    
    logging.info("Mappa generata con successo.")

def run_full_workflow():
    """Funzione di orchestrazione che unisce i due processi."""
    logging.info("=== Avvio Workflow Completo ===")
    
    generate_world_map()
    
    print("\n" + "="*40 + "\n") # Separatore visivo in console

    logging.info("=== Workflow Completato Con Successo ===")
    
if __name__ == "__main__":
    run_full_workflow()