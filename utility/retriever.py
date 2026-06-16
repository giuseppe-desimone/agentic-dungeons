import h5py
import os

def get_map_data(file_path):
    if not os.path.exists(file_path):
        print(f"Errore: File non trovato in '{file_path}'")
        return

    # Definizione del mapping (Etichetta, Chiave HDF5, Unità di misura)
    mapping = [
        ("Elevation", "elevation_meters", "m"),
        ("Humidity", "humidity_percentage", "%"),
        ("Watermap", "surface_runoff_mm", "mm/anno"),
        ("River map", "river_flow_m3s", "m³/s"),
        ("Precipitation", "precipitation_mm", "mm/anno"),
        ("Temperature", "temperature_celsius", "°C"),
        ("Biomes", "biome_names", "")
    ]

    try:
        with h5py.File(file_path, 'r') as f:
            if 'normalized_data' not in f:
                print("Errore: Gruppo 'normalized_data' non trovato.")
                return

            group = f['normalized_data']
            
            print("--- ISPEZIONE MAPPA HDF5 ---")
            print("Inserisci 'X Y' (es: 250 120) o 'exit' per uscire.")

            while True:
                user_input = input("\n> ").strip().lower()
                
                if user_input == 'exit':
                    break
                
                parts = user_input.split()
                if len(parts) != 2:
                    print("Usa il formato: intero intero (es. 150 300)")
                    continue
                
                try:
                    x, y = int(parts[0]), int(parts[1])
                except ValueError:
                    print("Inserisci solo numeri interi.")
                    continue

                # CORREZIONE 1: Controllo dei limiti coerente (X < 1024, Y < 512)
                if not (0 <= x < 1024 and 0 <= y < 512):
                    print("Coordinate fuori limite! Limiti massimi -> X: 1023, Y: 511.")
                    continue

                print(f"\n[Coordinate: X={x}, Y={y}]")
                print("-" * 35)

                for label, key, unit in mapping:
                    if key in group:
                        # CORREZIONE 2: L'indicizzazione delle matrici vuole [RIGA, COLONNA] -> [Y, X]
                        val = group[key][y, x]
                        
                        if isinstance(val, bytes):
                            val = val.decode('utf-8')
                        
                        val_str = f"{val} {unit}".strip()
                        print(f"{label:<15} : {val_str}")
                    else:
                        print(f"{label:<15} : n/d")
                        
    except Exception as e:
        print(f"Errore: {e}")

if __name__ == "__main__":
    path = "assets/map/world.world" 
    get_map_data(path)