import logging
from src.map_generator import WorldEngineRunner, WorldConfig

# Configurazione base per visualizzare i log sulla console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    world_cfg = WorldConfig
    world_cfg.WORLD_NAME = "test"
    world_cfg.WIDTH = 1024
    world_cfg.HEIGHT = 512
    world_cfg.NUM_PLATES = 15

    
    runner = WorldEngineRunner(world_cfg)
    runner.run()
    
    logging.info("\nWorkflow completed successfully.")
