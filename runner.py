import logging
from src.world.world_generator import WorldEngineRunner, WorldConfig
from utility.retriever import get_world_data

# Configurazione base per visualizzare i log sulla console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def generate_world():
    """Fase 1: Generazione del mondo e analisi dei POI tramite Python."""
    logging.info("Inizio generazione del mondo...")
    
    world_cfg = WorldConfig
    world_cfg.WORLD_NAME = "world"
    world_cfg.WIDTH = 1000
    world_cfg.HEIGHT = 500
    world_cfg.NUM_PLATES = 15

    runner = WorldEngineRunner(world_cfg)
    runner.run()
    
    logging.info("Mondo generato con successo.")

def run_full_workflow():
    """Funzione di orchestrazione che unisce i due processi."""
    logging.info("=== Avvio Workflow Completo ===")
    
    generate_world()
    
    print("\n" + "="*40 + "\n") # Separatore visivo in console

    get_world_data("assets/world/world.world")  # Analizza il file HDF5 generato

    logging.info("=== Workflow Completato Con Successo ===")
    
if __name__ == "__main__":
    run_full_workflow()