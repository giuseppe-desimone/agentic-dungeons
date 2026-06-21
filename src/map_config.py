import random

MIN_CELSIUS = random.randint(-80, -70) # Temperatura minima reale desiderata
MAX_CELSIUS = random.randint(50, 60) # Temperatura massima reale desiderata

MAX_ALTITUDE = random.randint(8000, 10000) # altezza desiderata in metri del picco più alto al mondo.
MIN_ABYSS = 50

PLANET_RADIOUS = 3185000


biome_colors = {
    "ocean": (23, 94, 145),
    "sea": (23, 94, 145),
    "ice": (255, 255, 255),
    "subpolar dry tundra": (128, 128, 128),
    "subpolar moist tundra": (96, 128, 128),
    "subpolar wet tundra": (64, 128, 128),
    "subpolar rain tundra": (32, 128, 192),
    "polar desert": (192, 192, 192),
    "boreal desert": (160, 160, 128),
    "cool temperate desert": (192, 192, 128),
    "warm temperate desert": (224, 224, 128),
    "subtropical desert": (240, 240, 128),
    "tropical desert": (255, 255, 128),
    "boreal rain forest": (32, 160, 192),
    "cool temperate rain forest": (32, 192, 192),
    "warm temperate rain forest": (32, 224, 192),
    "subtropical rain forest": (32, 240, 176),
    "tropical rain forest": (32, 255, 160),
    "boreal wet forest": (64, 160, 144),
    "cool temperate wet forest": (64, 192, 144),
    "warm temperate wet forest": (64, 224, 144),
    "subtropical wet forest": (64, 240, 144),
    "tropical wet forest": (64, 255, 144),
    "boreal moist forest": (96, 160, 128),
    "cool temperate moist forest": (96, 192, 128),
    "warm temperate moist forest": (96, 224, 128),
    "subtropical moist forest": (96, 240, 128),
    "tropical moist forest": (96, 255, 128),
    "warm temperate dry forest": (128, 224, 128),
    "subtropical dry forest": (128, 240, 128),
    "tropical dry forest": (128, 255, 128),
    "boreal dry scrub": (128, 160, 128),
    "cool temperate desert scrub": (160, 192, 128),
    "warm temperate desert scrub": (192, 224, 128),
    "subtropical desert scrub": (208, 240, 128),
    "tropical desert scrub": (224, 255, 128),
    "cool temperate steppe": (128, 192, 128),
    "warm temperate thorn scrub": (160, 224, 128),
    "subtropical thorn woodland": (176, 240, 128),
    "tropical thorn woodland": (192, 255, 128),
    "tropical very dry forest": (160, 255, 128),
    }

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
    NUM_PLATES = 15               # -q
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
