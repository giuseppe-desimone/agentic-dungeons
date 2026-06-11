import sys, os
from PIL import Image
import numpy as np
import h5py
import logging
from worldengine.cli.main import main
from src.map_config import WorldConfig, biome_colors, MAX_CELSIUS, MIN_CELSIUS

# Configurazione logger locale
logger = logging.getLogger(__name__)

"""
usage: usage: worldengine [options] [world|plates|ancient_map|info|export]

positional arguments:
  OPERATOR
  FILE

options:
  -h, --help            show this help message and exit
  -o DIR, --output-dir DIR
                        generate files in DIR [default = '.']
  -n STR, --worldname STR
                        set world name to STR. output is stored in a world file with the name format
                        'STR.world'. If a name is not provided, then seed_N.world, where N=SEED
  --hdf5                Save world file using HDF5 format. Default = store using protobuf format
  -s N, --seed N        Use seed=N to initialize the pseudo-random generation. If not provided, one will be     
                        selected for you.
  -t STR, --step STR    Use step=[plates|precipitations|full] to specify how far to proceed in the world        
                        generation process. [default='full']
  -x N, --width N       N = width of the world to be generated [default=512]
  -y N, --height N      N = height of the world to be generated [default=512]
  -q N, --number-of-plates N
                        N = number of plates [default = 10]
  --recursion_limit N   Set the recursion limit [default = 2000]
  -v, --verbose         Enable verbose messages
  --version             Display version information
  --bw, --black-and-white
                        generate maps in black and white

Generate Options:
  These options are only useful in plate and world modes

  -r, --rivers          generate rivers map
  --gs, --grayscale-heightmap
                        produce a grayscale heightmap
  --ocean_level N       elevation cut off for sea level " +[default = 1.0]
  --temps #/#/#/#/#/#   Provide alternate ranges for temperatures. If not provided, the default values will be  
                        used. [default = .126/.235/.406/.561/.634/.876]
  --humidity #/#/#/#/#/#/#
                        Provide alternate ranges for humidities. If not provided, the default values will be    
                        used. [default = .059/.222/.493/.764/.927/.986/.998]
  -gv N, --gamma-value N
                        N = Gamma value for temperature/precipitation gamma correction curve. [default = 1.25]  
  -go N, --gamma-offset N
                        N = Adjustment value for temperature/precipitation gamma correction curve. [default =   
                        .2]
  --not-fade-borders    Not fade borders
  --scatter             generate scatter plot
  --sat                 generate satellite map
  --ice                 generate ice caps map

Ancient Map Options:
  These options are only useful in ancient_map mode

  -w FILE, --worldfile FILE
                        FILE to be loaded
  -g FILE, --generatedfile FILE
                        name of the FILE
  -f N, --resize-factor N
                        resize factor (only integer values). Note this can only be used to increase the size    
                        of the map [default=1]
  --sea_color S         string for color [blue|brown]
  --not-draw-biome      Not draw biome
  --not-draw-mountains  Not draw mountains
  --not-draw-rivers     Not draw rivers
  --draw-outer-border   Draw outer land border

Export Options:
  You can specify the formats you wish the generated output to be in.

  --export-format STR   Export to a specific format such as BMP or PNG. All possible formats:
                        http://www.gdal.org/formats_list.html
  --export-datatype STR
                        Type of stored data (e.g. uint16, int32, float32 and etc.)
  --export-dimensions EXPORT_DIMENSIONS EXPORT_DIMENSIONS
                        Export to desired dimensions. (e.g. 4096 4096)
  --export-normalize EXPORT_NORMALIZE EXPORT_NORMALIZE
                        Normalize the data set to between min and max. (e.g. 0 255)
  --export-subset EXPORT_SUBSET EXPORT_SUBSET EXPORT_SUBSET EXPORT_SUBSET
                        Normalize the data set to between min and max?
"""

class WorldEngineRunner:
    """
    Gestisce la costruzione degli argomenti e l'esecuzione di WorldEngine.
    """
    
    def __init__(self, config):
        """
        Inizializza il runner con un oggetto di configurazione (classe o istanza).
        """
        self.cfg = config

    def _build_arguments(self):
        """
        Costruisce la lista degli argomenti CLI basandosi sulla configurazione.
        """
        params = []
        c = self.cfg # Short alias per comodità

        # Positional Arguments
        if c.OPERATOR:
            params.append(c.OPERATOR)
        if c.INPUT_FILE and c.OPERATOR in ["info", "export"]:
            params.append(c.INPUT_FILE)

        # Standard Options
        if c.OUTPUT_DIR:
            params.extend(["--output-dir", c.OUTPUT_DIR])
        if c.WORLD_NAME:
            params.extend(["--worldname", c.WORLD_NAME])
        if c.USE_HDF5:
            params.append("--hdf5")
        if c.SEED is not None:
            params.extend(["--seed", str(c.SEED)])
        if c.STEP:
            params.extend(["--step", c.STEP])
        if c.WIDTH:
            params.extend(["--width", str(c.WIDTH)])
        if c.HEIGHT:
            params.extend(["--height", str(c.HEIGHT)])
        if c.NUM_PLATES:
            params.extend(["--number-of-plates", str(c.NUM_PLATES)])
        if c.RECURSION_LIMIT:
            params.extend(["--recursion_limit", str(c.RECURSION_LIMIT)])
        if c.VERBOSE:
            params.append("--verbose")
        if c.BLACK_AND_WHITE:
            params.append("--black-and-white")

        # Generate Options
        if c.GENERATE_RIVERS:
            params.append("--rivers")
        if c.GENERATE_GRAYSCALE:
            params.append("--grayscale-heightmap")
        if c.GENERATE_SCATTER:
            params.append("--scatter")
        if c.GENERATE_SATELLITE:
            params.append("--sat")
        if c.GENERATE_ICE:
            params.append("--ice")
        
        if c.OCEAN_LEVEL is not None:
            params.extend(["--ocean_level", str(c.OCEAN_LEVEL)])
        if c.NOT_FADE_BORDERS:
            params.append("--not-fade-borders")
        if c.GAMMA_VALUE is not None:
            params.extend(["--gamma-value", str(c.GAMMA_VALUE)])
        if c.GAMMA_OFFSET is not None:
            params.extend(["--gamma-offset", str(c.GAMMA_OFFSET)])
        if c.TEMPS_RANGES:
            params.extend(["--temps", c.TEMPS_RANGES])
        if c.HUMIDITY_RANGES:
            params.extend(["--humidity", c.HUMIDITY_RANGES])

        # Ancient Map Options
        if c.OPERATOR == "ancient_map":
            if c.ANCIENT_WORLD_FILE:
                params.extend(["--worldfile", c.ANCIENT_WORLD_FILE])
            if c.ANCIENT_GEN_FILE:
                params.extend(["--generatedfile", c.ANCIENT_GEN_FILE])
            if c.RESIZE_FACTOR:
                params.extend(["--resize-factor", str(c.RESIZE_FACTOR)])
            if c.SEA_COLOR:
                params.extend(["--sea_color", c.SEA_COLOR])
            
            # Handle "Not" flags.
            if not c.DRAW_BIOME:
                params.append("--not-draw-biome")
            if not c.DRAW_MOUNTAINS:
                params.append("--not-draw-mountains")
            if not c.DRAW_RIVERS:
                params.append("--not-draw-rivers")
                
            if c.DRAW_OUTER_BORDER:
                params.append("--draw-outer-border")

        # Export Options
        if c.OPERATOR == "export":
            if c.EXPORT_FORMAT:
                params.extend(["--export-format", c.EXPORT_FORMAT])
            if c.EXPORT_DATATYPE:
                params.extend(["--export-datatype", c.EXPORT_DATATYPE])
            if c.EXPORT_DIMENSIONS:
                params.append("--export-dimensions")
                params.extend([str(x) for x in c.EXPORT_DIMENSIONS])
            if c.EXPORT_NORMALIZE:
                params.append("--export-normalize")
                params.extend([str(x) for x in c.EXPORT_NORMALIZE])
            if c.EXPORT_SUBSET:
                params.append("--export-subset")
                params.extend([str(x) for x in c.EXPORT_SUBSET])
                
        return params
    
    def _generate_submap_dimentional_data(self):
        """
        Calcola i dati dimensionali per ogni riga (latitudine) della mappa:
        1. Larghezza del pixel in metri (dataset_widths)
        2. Area del pixel in metri quadri (dataset_area)
        3. Lato di un quadrato equivalente all'area (dataset_sqr_sides)
        4. Numero di 'tile' reali che entrano nell'anello (dataset_real_tiles_per_row)
        """
        rows = self.cfg.HEIGHT
        cols = self.cfg.WIDTH
        EARTH_RADIUS = 6_371_000

        # 1. Altezza costante del pixel (distanza Nord-Sud)
        pixel_height = (np.pi * EARTH_RADIUS) / rows

        # 2. Latitudini
        step_lat = 180.0 / rows
        latitudes_deg = np.linspace(90 - (step_lat/2), -90 + (step_lat/2), rows)
        latitudes_rad = np.radians(latitudes_deg)

        # DATASET 1: Larghezza pixel (variabile con la latitudine)
        pixel_widths = (2 * np.pi * EARTH_RADIUS * np.cos(latitudes_rad)) / cols
        
        # DATASET 2: Area
        areas = pixel_widths * pixel_height
        
        # DATASET 3: Lato quadrato equivalente
        sqr_sides = np.sqrt(np.maximum(areas, 0))
        
        # DATASET 4: Conteggio Tile Reali (Densità anello)
        exact_counts = cols * np.cos(latitudes_rad)
        # Arrotondiamo e assicuriamo almeno 1 pixel
        integer_counts = np.round(exact_counts).astype(np.int32)
        integer_counts = np.maximum(integer_counts, 1)

        # SALVATAGGIO DATASETS (Casting a int32 per risparmiare spazio e pulizia)
        dataset_widths = np.round(pixel_widths).astype(np.int32)
        dataset_area = np.round(areas).astype(np.int32)
        dataset_sqr_sides = np.round(sqr_sides).astype(np.int32)
        dataset_real_tiles_per_row = integer_counts
        
        return dataset_widths, dataset_area, dataset_sqr_sides, dataset_real_tiles_per_row, EARTH_RADIUS

    def _inject_dimensions_into_hdf5(self, widths, areas, sides, tiles_per_row, radius):
        """
        Inietta i 4 dataset dimensionali (array 1D) nel file HDF5.
        """
        output_dir = getattr(self.cfg, 'OUTPUT_DIR', os.path.join("assets", "map"))
        file_path = os.path.join(output_dir, f"{self.cfg.WORLD_NAME}.world")

        if not os.path.exists(file_path):
            logger.error(f"Errore: Il file {file_path} non esiste.")
            return

        logger.info(f"--- Injecting Dimensional Data into {file_path} ---")

        try:
            with h5py.File(file_path, 'r+') as f:
                group_name = "dimensional_data"
                if group_name in f: del f[group_name] 
                
                grp = f.create_group(group_name)

                # --- 1. Pixel Widths ---
                dset_w = grp.create_dataset("pixel_width_per_row", data=widths)
                dset_w.attrs["unit"] = "meters"
                dset_w.attrs["description"] = "Width of a pixel in meters at this latitude row"

                # --- 2. Pixel Areas ---
                dset_a = grp.create_dataset("pixel_area_per_row", data=areas)
                dset_a.attrs["unit"] = "square meters"
                dset_a.attrs["description"] = "Area of a single pixel at this latitude row"

                # --- 3. Equivalent Side ---
                dset_s = grp.create_dataset("pixel_sqr_side_per_row", data=sides)
                dset_s.attrs["unit"] = "meters"
                dset_s.attrs["description"] = "Side length of a square with area equivalent to the pixel"
                dset_s.attrs["radius_used"] = radius

                # --- 4. Tiles per Row (Ring Density) ---
                dset_c = grp.create_dataset("valid_tiles_per_row", data=tiles_per_row)
                dset_c.attrs["description"] = "Number of non-distorted 'real' squares fitting in this latitude ring"
                dset_c.attrs["max_cols"] = self.cfg.WIDTH

                # Statistiche rapide per debug
                mid_idx = len(widths) // 2
                logger.info(f"Datasets injected into group '{group_name}':")
                logger.info(f" > Equator Width:  {widths[mid_idx]} m | Area: {areas[mid_idx]} m^2 | Count: {tiles_per_row[mid_idx]}")
                logger.info(f" > Pole Width:     {widths[0]} m       | Area: {areas[0]} m^2       | Count: {tiles_per_row[0]}")

        except Exception as e:
            logger.error(f"Errore durante l'iniezione HDF5: {e}", exc_info=True)

    def _rgb_to_biome_name(self, img_array):
        """
        Converte un array numpy (H, W, 3) in un array (H, W) di stringhe
        basandosi sul dizionario biome_colors.
        """
        rows, cols, _ = img_array.shape
        biome_names_map = np.full((rows, cols), "ocean", dtype=object)

        logger.info("--- Mapping pixels to biome names (this might take a moment) ---")
        
        for name, color_tuple in biome_colors.items():
            color_array = np.array(color_tuple)
            mask = np.all(img_array == color_array, axis=-1)
            
            if np.any(mask):
                biome_names_map[mask] = name
        
        return biome_names_map

    def _elevation_to_meters(self, elevation_array, sea_val, plain_val, hill_val):
        """
        Converte l'elevazione astratta in metri.
        Mappa i threshold dinamici letti dal file: sea -> 0m, plain -> 300m, hill -> 600m.
        Estrapola i valori esterni (es. montagne o fondali oceanici).
        """
        meters_array = np.zeros_like(elevation_array, dtype=np.float32)

        # Segmento 1: Sotto e fino alla pianura (include fondali marini)
        mask_lower = elevation_array <= plain_val
        scale_lower = 300.0 / (plain_val - sea_val) if plain_val != sea_val else 1.0
        meters_array[mask_lower] = (elevation_array[mask_lower] - sea_val) * scale_lower

        # Segmento 2: Sopra la pianura (colline e montagne)
        mask_upper = elevation_array > plain_val
        scale_upper = 300.0 / (hill_val - plain_val) if hill_val != plain_val else 1.0
        meters_array[mask_upper] = 300.0 + (elevation_array[mask_upper] - plain_val) * scale_upper

        # Arrotonda e converte in Interi
        return np.round(meters_array).astype(np.int32)

    def _humidity_to_percentage(self, humidity_array, min_val, max_val):
        """
        Mappa i valori di umidità in percentuale [0, 100] basandosi 
        sui valori minimi e massimi estratti dinamicamente dal dataset.
        """
        delta = max_val - min_val
        if delta == 0:
            return np.zeros_like(humidity_array, dtype=np.int32)
            
        # Normalizza l'array tra 0.0 e 1.0 usando i minimi e massimi reali
        normalized = (humidity_array - min_val) / delta
        
        # Scala a 0-100 e limita per sicurezza
        percentage = np.clip(normalized * 100.0, 0, 100)
        
        return np.round(percentage).astype(np.int32)

    def _watermap_to_runoff(self, water_array, max_val):
        """
        Converte la watermap in deflusso superficiale (mm/anno).
        Mappa dinamicamente dal valore 0 al valore massimo del dataset (fino a ~2000 mm).
        """
        MAX_RUNOFF_MM = 2000.0
        runoff_array = np.zeros_like(water_array, dtype=np.float32)
        
        mask = water_array > 0
        if max_val > 0:
            runoff_array[mask] = (water_array[mask] / max_val) * MAX_RUNOFF_MM
            
        return np.round(runoff_array).astype(np.int32)

    def _river_map_to_flow(self, river_array, max_river_val):
        """
        Converte la river_map in portata d'acqua (m³/s) usando il massimo dinamico.
        La portata massima realistica impostata è 6500 m³/s.
        """
        MAX_FLOW_M3S = 6500.0
        flow_array = np.zeros_like(river_array, dtype=np.float32)
        
        mask_river = river_array > 0
        if max_river_val > 0:
            flow_array[mask_river] = (river_array[mask_river] / max_river_val) * MAX_FLOW_M3S
            
        return np.round(flow_array).astype(np.int32)
    
    def _precipitation_to_mm(self, precip_array, min_val, low_val, med_val, max_val):
        """
        Converte le precipitazioni di WorldEngine (float [-1.0, 1.0]) in mm/anno reali.
        Usa interpolazione lineare su più segmenti basati sui threshold dinamici.
        """
        # Creiamo gli array delle soglie e dei valori reali corrispondenti
        # Nota: np.interp richiede che l'asse X sia in ordine crescente
        x_vals = [min_val, low_val, med_val, max_val]
        y_vals = [0.0, 250.0, 1000.0, 4000.0]  # mm/anno
        
        # Interpolazione lineare vettorizzata
        mm_array = np.interp(precip_array, x_vals, y_vals)
        
        # Arrotonda e converte in Interi
        return np.round(mm_array).astype(np.int32)

    def _temperature_to_celsius(self, temp_array, min_val, max_val, MAX_CELSIUS, MIN_CELSIUS):
        """
        Converte le temperature astratte in gradi Celsius tramite una semplice
        interpolazione lineare tra un valore minimo e massimo desiderato.
        """
        delta = max_val - min_val
        
        # Prevenzione divisione per zero nel caso di mappe uniformi
        if delta == 0:
            return np.full_like(temp_array, MIN_CELSIUS, dtype=np.int32)
            
        # Normalizza l'array di partenza tra 0.0 e 1.0
        normalized = (temp_array - min_val) / delta
        
        # Scala nel range Celsius desiderato
        celsius_array = MIN_CELSIUS + normalized * (MAX_CELSIUS - MIN_CELSIUS)
        
        return np.round(celsius_array).astype(np.int32)
    
    def _inject_normalized_data_in_hdf5(self):
        """
        1. Crea un gruppo 'normalized_data'.
        2. Elevation -> elevation_meters (int)
        3. Humidity -> humidity_percentage (int 0-100)
        4. Watermap -> surface_runoff_mm (int mm/anno)
        5. River map -> river_flow_m3s (int m³/s)
        6. Precipitation -> precipitation_mm (int mm/anno)
        7. Temperature -> temperature_celsius (int °C)
        8. Biomes -> biome_names (string)
        """
        output_dir = getattr(self.cfg, 'OUTPUT_DIR', os.path.join("assets", "map"))
        world_file = os.path.join(output_dir, f"{self.cfg.WORLD_NAME}.world")
        biome_img_path = os.path.join(output_dir, f"{self.cfg.WORLD_NAME}_biome.png")

        if not os.path.exists(world_file):
            logger.warning(f"File non trovato durante l'iniezione: {world_file}")
            return

        logger.info(f"\n--- Injecting Normalized Data into {world_file} ---")

        try:
            with h5py.File(world_file, 'r+') as f:
                # --- 1. CREAZIONE GRUPPO ---
                norm_grp = f.require_group('normalized_data')

                # --- 2. ELEVATION ---
                if 'elevation/data' in f and 'elevation/thresholds' in f:
                    data = f['elevation/data'][:]
                    sea = f['elevation/thresholds/sea'][()]
                    plain = f['elevation/thresholds/plain'][()]
                    hill = f['elevation/thresholds/hill'][()]

                    meters_matrix = self._elevation_to_meters(data, sea, plain, hill)

                    if 'elevation_meters' in norm_grp: del norm_grp['elevation_meters']
                    norm_grp.create_dataset('elevation_meters', data=meters_matrix, dtype='int32')
                    logger.info(f" > Elevation meters saved (Min: {np.min(meters_matrix)}m, Max: {np.max(meters_matrix)}m)")

                # --- 3. HUMIDITY ---
                if 'humidity/data' in f:
                    hum_data = f['humidity/data'][:]
                    min_hum = np.min(hum_data)
                    max_hum = np.max(hum_data)
                    
                    hum_percentage_matrix = self._humidity_to_percentage(hum_data, min_hum, max_hum)

                    if 'humidity_percentage' in norm_grp: del norm_grp['humidity_percentage']
                    norm_grp.create_dataset('humidity_percentage', data=hum_percentage_matrix, dtype='int32')
                    logger.info(f" > Humidity percentage saved.")

                # --- 4. WATERMAP (SURFACE RUNOFF) ---
                if 'watermap/data' in f:
                    water_data = f['watermap/data'][:]
                    max_water = np.max(water_data)
                    
                    runoff_matrix = self._watermap_to_runoff(water_data, max_water)

                    if 'surface_runoff_mm' in norm_grp: del norm_grp['surface_runoff_mm']
                    norm_grp.create_dataset('surface_runoff_mm', data=runoff_matrix, dtype='int32')
                    logger.info(f" > Surface runoff saved.")

                # --- 5. RIVER MAP (FLOW M³/S) ---
                if 'river_map' in f:
                    river_data = f['river_map'][:]
                    max_river = np.max(river_data)
                    
                    flow_matrix = self._river_map_to_flow(river_data, max_river)

                    if 'river_flow_m3s' in norm_grp: del norm_grp['river_flow_m3s']
                    norm_grp.create_dataset('river_flow_m3s', data=flow_matrix, dtype='int32')
                    logger.info(f" > River flow saved.")

                # --- 6. PRECIPITATION (MM/YEAR) ---
                if 'precipitation/data' in f and 'precipitation/thresholds' in f:
                    precip_data = f['precipitation/data'][:]
                    min_precip = np.min(precip_data)
                    max_precip = np.max(precip_data)
                    low_p = f['precipitation/thresholds/low'][()]
                    med_p = f['precipitation/thresholds/med'][()]

                    precip_mm_matrix = self._precipitation_to_mm(precip_data, min_precip, low_p, med_p, max_precip)

                    if 'precipitation_mm' in norm_grp: del norm_grp['precipitation_mm']
                    norm_grp.create_dataset('precipitation_mm', data=precip_mm_matrix, dtype='int32')
                    logger.info(f" > Precipitation (mm/year) saved (Min: {np.min(precip_mm_matrix)}mm, Max: {np.max(precip_mm_matrix)}mm)")

                # --- 7. TEMPERATURE (CELSIUS) ---
                if 'temperature/data' in f:
                    temp_data = f['temperature/data'][:]
                    
                    # Usiamo solo min e max del dataset per l'interpolazione lineare
                    min_temp = np.min(temp_data)
                    max_temp = np.max(temp_data)

                    celsius_matrix = self._temperature_to_celsius(temp_data, min_temp, max_temp, MAX_CELSIUS, MIN_CELSIUS)

                    if 'temperature_celsius' in norm_grp: del norm_grp['temperature_celsius']
                    norm_grp.create_dataset('temperature_celsius', data=celsius_matrix, dtype='int32')
                    logger.info(f" > Temperature Celsius saved (Min: {np.min(celsius_matrix)}°C, Max: {np.max(celsius_matrix)}°C)")

                # --- 8. BIOMES ---
                if os.path.exists(biome_img_path):
                    with Image.open(biome_img_path) as img:
                        img_arr = np.array(img.convert('RGB'))
                    
                    biome_names = self._rgb_to_biome_name(img_arr)
                    
                    if 'biome_names' in norm_grp: del norm_grp['biome_names']
                    dt = h5py.special_dtype(vlen=str)
                    norm_grp.create_dataset('biome_names', data=biome_names, dtype=dt)
                    logger.info(f" > Biome names saved.")
            
        except Exception as e:
            logger.error(f"Error injecting data: {e}", exc_info=True)
    
    def run(self):
        args_list = self._build_arguments()
        original_argv = sys.argv
        generation_successful = False

        try:
            sys.argv = ["worldengine_script"] + args_list
            logger.info(f"\n>>> Running Worldengine with: {' '.join(args_list)}\n")
            main()
            generation_successful = True
        except SystemExit as e:
            if e.code == 0 or e.code is None:
                logger.info(f"\n>>> Worldengine finished successfully.")
                generation_successful = True
            else:
                logger.error(f"\n>>> Worldengine failed (Exit Code: {e}).")
        except Exception as e:
            logger.error(f"\n>>> Error: {e}", exc_info=True)
        finally:
            sys.argv = original_argv
            
            if generation_successful:
                try:
                    logger.info("\n--- Calculating Earth Dimensions ---")
                    
                    # 2. Calcolo Unificato dei Dataset Dimensionali
                    (d_widths, d_areas, d_sides, d_counts, radius) = self._generate_submap_dimentional_data()
                    
                    # 3. Iniezione nel file HDF5
                    self._inject_dimensions_into_hdf5(d_widths, d_areas, d_sides, d_counts, radius)
                    
                    # 4. salvataggio Biomi (Interi -> Stringhe da Immagine)
                    self._inject_normalized_data_in_hdf5()
                except Exception as e:
                    logger.error(f"Error during post-generation processing: {e}", exc_info=True)
            
            logger.info(">>> Done.\n")

if __name__ == "__main__":
    WorldEngineRunner(WorldConfig).run()
