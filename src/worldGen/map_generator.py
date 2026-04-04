from map.map_engine import WorldEngineRunner, WorldConfig

if __name__ == "__main__":
    world_cfg = WorldConfig
    world_cfg.WORLD_NAME = "test"
    world_cfg.WIDTH = 1024
    world_cfg.HEIGHT = 512
    world_cfg.NUM_PLATES = 15

    
    runner = WorldEngineRunner(world_cfg)
    runner.run()
    
    print("\nWorkflow completed successfully.")