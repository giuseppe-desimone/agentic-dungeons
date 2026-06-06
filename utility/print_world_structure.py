import h5py
import numpy as np

def print_hdf5_structure(name, obj):
    """
    Funzione di callback per analizzare i nodi del file HDF5.
    Stampa valore per scalari, e Min/Max per matrici.
    """
    indent = "  " * name.count('/')
    
    if isinstance(obj, h5py.Dataset):
        # Info di base
        base_info = f"{indent}Dset: {name} | Shape: {obj.shape} | Type: {obj.dtype}"
        
        # Leggiamo il dato (dataset[()] carica il contenuto in memoria come numpy array)
        try:
            data = obj[()]
        except Exception:
            print(f"{base_info} | <Impossibile leggere i dati>")
            return

        # CASO 1: Valore Singolo (Scalare o array di dim 1)
        if obj.size == 1:
            # Gestione specifica per stringhe (spesso sono bytes in h5py)
            val_to_print = data
            if isinstance(data, bytes):
                val_to_print = data.decode('utf-8', errors='ignore')
            elif isinstance(data, np.ndarray):
                # Estrae il valore dall'array 0-d o 1-d
                val_to_print = data.item()
                if isinstance(val_to_print, bytes):
                    val_to_print = val_to_print.decode('utf-8', errors='ignore')
            
            print(f"{base_info} | Val: {val_to_print}")

        # CASO 2: Matrici / Array Multipli
        elif obj.size > 1:
            # Calcoliamo min/max solo se è un tipo numerico o booleano
            if np.issubdtype(obj.dtype, np.number) or obj.dtype == bool:
                min_val = np.min(data)
                max_val = np.max(data)
                
                # Formattazione per pulizia (evita troppi decimali se float)
                if obj.dtype.kind == 'f':
                    print(f"{base_info} | Min: {min_val:.4f} | Max: {max_val:.4f}")
                else:
                    print(f"{base_info} | Min: {min_val} | Max: {max_val}")
            else:
                # Se è un array di oggetti/stringhe complesse, non stampiamo min/max
                print(f"{base_info} | <Dati complessi/String Array>")
                
    elif isinstance(obj, h5py.Group):
        print(f"{indent}Group: {name}")

def analyze_file(filename):
    try:
        with h5py.File(filename, 'r') as f:
            print(f"--- Struttura e Valori del file: {filename} ---")
            f.visititems(print_hdf5_structure)
    except Exception as e:
        print(f"Errore durante l'apertura del file: {e}")

if __name__ == "__main__":
    # Inserisci qui il percorso del tuo file
    file_path = "assets/map/test.world" 
    analyze_file(file_path)