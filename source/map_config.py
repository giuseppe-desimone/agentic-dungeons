import random

MIN_CELSIUS = random.randint(-80, -70) # Temperatura minima reale desiderata
MAX_CELSIUS = random.randint(50, 60) # Temperatura massima reale desiderata

MAX_ALTITUDE = random.randint(8000, 10000) # altezza desiderata in metri del picco più alto al mondo.
MIN_ABYSS = 50

PLANET_RADIOUS = 3185000

biome_codes = {
    "boreal desert": 0,
    "boreal dry scrub": 1,
    "boreal moist forest": 2,
    "boreal rain forest": 3,
    "boreal wet forest": 4,
    "cool temperate desert": 5,
    "cool temperate desert scrub": 6,
    "cool temperate moist forest": 7,
    "cool temperate rain forest": 8,
    "cool temperate steppe": 9,
    "cool temperate wet forest": 10,
    "ice": 11,
    "ocean": 12,
    "polar desert": 13,
    "sea": 14,
    "subpolar dry tundra": 15,
    "subpolar moist tundra": 16,
    "subpolar rain tundra": 17,
    "subpolar wet tundra": 18,
    "subtropical desert": 19,
    "subtropical desert scrub": 20,
    "subtropical dry forest": 21,
    "subtropical moist forest": 22,
    "subtropical rain forest": 23,
    "subtropical thorn woodland": 24,
    "subtropical wet forest": 25,
    "tropical desert": 26,
    "tropical desert scrub": 27,
    "tropical dry forest": 28,
    "tropical moist forest": 29,
    "tropical rain forest": 30,
    "tropical thorn woodland": 31,
    "tropical very dry forest": 32,
    "tropical wet forest": 33,
    "warm temperate desert": 34,
    "warm temperate desert scrub": 35,
    "warm temperate dry forest": 36,
    "warm temperate moist forest": 37,
    "warm temperate rain forest": 38,
    "warm temperate thorn scrub": 39,
    "warm temperate wet forest": 40,
}

biome_names_by_code = {v: k for k, v in biome_codes.items()}

class WorldConfig:
    """
    Classe contenente tutte le configurazioni per la generazione del mondo.
    """
    
    # --- 1. OPERATION & BASIC INFO ---
    # Options: "world", "plates", "ancient_map", "info", "export"
    OPERATOR = "world" 
    
    # Used for info/export/ancient_map (input file)
    INPUT_FILE = None  
    
    # Output settings
    OUTPUT_DIR = "assets/map"
    WORLD_NAME = "world"          # -n
    USE_HDF5 = True               # --hdf5
    
    # --- 2. GENERATION PARAMETERS ---
    SEED = random.randint(0, 9999)# -s (cool ones: 3221, )
    WIDTH = 1000                  # -x
    HEIGHT = 500                  # -y
    NUM_PLATES = 7                # -q
    STEP = "full"                 # -t [plates|precipitations|full]
    RECURSION_LIMIT = 2000        # --recursion_limit
    
    # --- 3. GENERATE OPTIONS (Flags & Values) ---
    VERBOSE = True                # -v
    BLACK_AND_WHITE = False       # --bw
    
    GENERATE_RIVERS = True        # -r
    GENERATE_GRAYSCALE = False    # --gs
    GENERATE_SCATTER = False      # --scatter
    GENERATE_SATELLITE = True     # --sat
    GENERATE_ICE = True           # --ice
    
    OCEAN_LEVEL = 1.0             # --ocean_level
    NOT_FADE_BORDERS = True       # --not-fade-borders (Set True to prevent fading)
    
    # Gamma Correction
    GAMMA_VALUE = 1.25            # -gv
    GAMMA_OFFSET = 0.2            # -go
    
    # Custom Ranges (String format as per help, or None to use default)
    # Example: ".126/.235/.406/.561/.634/.876"
    TEMPS_RANGES = None           # --temps
    HUMIDITY_RANGES = None        # --humidity
    
    # --- 4. ANCIENT MAP OPTIONS (Only if OPERATOR = "ancient_map") ---
    # Note: Requires INPUT_FILE to be set or -w argument
    ANCIENT_WORLD_FILE = None     # -w (File to load)
    ANCIENT_GEN_FILE = None       # -g (Output filename)
    RESIZE_FACTOR = 1             # -f
    SEA_COLOR = "brown"           # --sea_color [blue|brown]
    
    # Ancient Map Flags (Note: Logic is inverted in CLI "--not-draw-X")
    # Here: True = Draw it, False = Don't draw it
    DRAW_BIOME = True             
    DRAW_MOUNTAINS = True
    DRAW_RIVERS = True
    DRAW_OUTER_BORDER = False     # This one is standard (True = Draw)

    # --- 5. EXPORT OPTIONS (Only if OPERATOR = "export") ---
    EXPORT_FORMAT = "PNG"         # --export-format
    EXPORT_DATATYPE = "uint16"    # --export-datatype
    # Tuple (x, y) or None
    EXPORT_DIMENSIONS = None      # --export-dimensions 4096 4096
    # Tuple (min, max) or None
    EXPORT_NORMALIZE = None       # --export-normalize 0 255
    # Tuple (x, y, w, h) or None
    EXPORT_SUBSET = None          # --export-subset
