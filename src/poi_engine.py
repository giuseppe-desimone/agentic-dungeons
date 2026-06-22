import os
import h5py
import numpy as np
import logging

logger = logging.getLogger(__name__)

class POIEngine:
    def __init__(self, config):
        self.cfg = config
        self.output_dir = getattr(config, 'OUTPUT_DIR', "assets/map")
        self.world_file = os.path.join(self.output_dir, f"{config.WORLD_NAME}.world")

    def extract_pois(self, num_civilizations=5, min_distance_pixels=40):
        """
        Analizza la mappa HDF5 per trovare i migliori POI (Punti di Interesse),
        garantendo la massima dispersione sia di distanza che di latitudine.
        
        :param num_civilizations: Numero di POI (capitali) da trovare.
        :param min_distance_pixels: Distanza minima reale garantita tra i POI.
        """
        if not os.path.exists(self.world_file):
            logger.error(f"File .world non trovato: {self.world_file}")
            return []

        # --- FASE 1: CARICAMENTO DEI LAYER DA HDF5 ---
        with h5py.File(self.world_file, 'r') as f:
            if 'normalized_data' not in f:
                logger.error("Dati normalizzati non trovati nell'HDF5. Esegui prima il map_generator.")
                return []
            
            norm_grp = f['normalized_data']
            elevation = norm_grp['elevation_meters'][:]
            temperature = norm_grp['temperature_celsius'][:]
            ocean_presence = norm_grp['ocean_presence'][:]
            river_flow = norm_grp['river_flow_m3s'][:]
            lake_presence = norm_grp['lake_presence'][:]
            # Convertiamo l'array di byte/oggetti in stringhe standard Python
            biome_names = norm_grp['biome_names'][:].astype(str)

        height, width = elevation.shape

        # --- FASE 2: CALCOLO SCORE DI ATTRATTIVITÀ BASE ---
        score_map = np.zeros((height, width), dtype=np.float32)
        
        # Filtro stringente di abitabilità (Niente oceani, temperature umane, sopra il livello del mare)
        habitable_mask = (~ocean_presence) & (temperature > -15) & (temperature < 40) & (elevation >= 0)
        
        # 1. Bonus Acqua Dolce (Fiumi e Laghi)
        river_bonus = np.clip(river_flow / 500.0, 0, 5.0) 
        score_map[river_bonus > 0] += river_bonus[river_bonus > 0]
        score_map[lake_presence] += 3.0  

        # 2. Bonus/Malus Altitudine (valli fertili vs montagne)
        score_map[(elevation >= 0) & (elevation < 600)] += 2.0
        score_map[(elevation >= 600) & (elevation < 1500)] += 0.5
        score_map[elevation >= 1500] -= 2.0 

        # 3. Bonus Bioma
        for biome_target, bonus in [("forest", 2.0), ("steppe", 1.5), ("desert", -4.0), ("tundra", -3.0)]:
            mask = np.char.find(biome_names, biome_target) != -1
            score_map[mask] += bonus

        # Applichiamo la maschera finale: se non è abitabile, il punteggio crolla a -100
        score_map[~habitable_mask] = -100.0

        # --- FASE 3: SELEZIONE ITERATIVA (GREEDY SIFTING) ---
        pois = []
        working_score = score_map.copy()

        # Ottimizzazione: Generiamo la griglia cartesiana H x W UNA SOLA VOLTA fuori dal ciclo
        y_grid, x_grid = np.mgrid[:height, :width]

        for i in range(num_civilizations):
            # Trova l'indice del pixel con il punteggio massimo rimasto nel mondo
            max_idx = np.argmax(working_score)
            y_max, x_max = np.unravel_index(max_idx, working_score.shape)
            
            if working_score[y_max, x_max] < -50:
                logger.warning(f"Trovati solo {len(pois)} POI validi sui {num_civilizations} richiesti.")
                break
                
            poi_info = {
                "id": i + 1,
                "x": int(x_max),
                "y": int(y_max),
                "score": round(float(score_map[y_max, x_max]), 2),
                "elevation": int(elevation[y_max, x_max]),
                "temperature": int(temperature[y_max, x_max]),
                "biome": str(biome_names[y_max, x_max]),
                "river_flow": int(river_flow[y_max, x_max]),
                "near_lake": bool(lake_presence[y_max, x_max])
            }
            pois.append(poi_info)

            # --- FASE 4: AGGIORNAMENTO DINAMICO DELLA MAPPA (INCENERIMENTO) ---
            
            # Calcolo della distanza orizzontale con WRAPPING (Mondo Cilindrico)
            dx = np.minimum(np.abs(x_grid - x_max), width - np.abs(x_grid - x_max))
            dy = np.abs(y_grid - y_max)
            
            # Compensazione distorsione equirettangolare
            lat_factor = np.cos(np.pi * (y_max / (height - 1) - 0.5))
            lat_factor = max(0.1, lat_factor) 
            
            distance_matrix = np.sqrt((dx * lat_factor)**2 + dy**2)
            
            # Forziamo l'azzeramento sul working_score
            working_score = np.where(distance_matrix < min_distance_pixels, -100.0, working_score)

            # Correzione della Latitudine (Malus sfumato per migrare Nord/Sud)
            lat_soft_buffer = int(height * 0.15)
            lat_distance = np.abs(y_grid - y_max)
            lat_malus = np.clip(1.0 - (lat_distance / lat_soft_buffer), 0, 1) * 6.0
            
            working_score -= lat_malus

        logger.info(f"Identificati {len(pois)} Punti di Interesse bilanciati e distanziati con successo.")
        return pois