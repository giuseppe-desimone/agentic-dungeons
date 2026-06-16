import h5py
import os
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

def get_map_data(file_path):
    if not os.path.exists(file_path):
        print(f"Errore: File HDF5 non trovato in '{file_path}'")
        return

    # Mappatura dei file immagine associati ai tasti 1-5
    map_images = {
        '1': ("Biome", "assets/map/world_biome.png"),
        '2': ("Elevation", "assets/map/world_elevation.png"),
        '3': ("Precipitation", "assets/map/world_precipitation.png"),
        '4': ("Satellite", "assets/map/world_satellite.png"),
        '5': ("Temperature", "assets/map/world_temperature.png")
    }

    # Mapping completo dei dataset
    mapping = [
        ("Elevation", "elevation_meters", "m"),
        ("Humidity", "humidity_percentage", "%"),
        ("Icecaps", "icecaps_percentage", "%"),
        ("Lake Presence", "lake_presence", ""),
        ("Ocean Presence", "ocean_presence", ""),
        ("Permeability", "permeability_percentage", "%"),
        ("Precipitation", "precipitation_mm", "mm/anno"),
        ("River Map (Flow)", "river_flow_m3s", "m³/s"),
        ("Watermap (Runoff)", "surface_runoff_mm", "mm/anno"),
        ("Temperature", "temperature_celsius", "°C"),
        ("Biomes", "biome_names", "")
    ]

    # Caricamento preventivo delle immagini
    loaded_images = {}
    for key, (label, img_path) in map_images.items():
        if os.path.exists(img_path):
            try:
                loaded_images[key] = (label, Image.open(img_path))
            except Exception as e:
                print(f"Avviso: Impossibile caricare {img_path}: {e}")
        else:
            print(f"Avviso: Immagine non trovata -> {img_path}")

    if not loaded_images:
        print("Errore: Nessuna immagine di mappa trovata in 'assets/map/'.")
        return

    try:
        with h5py.File(file_path, 'r') as f:
            if 'normalized_data' not in f:
                print("Errore: Gruppo 'normalized_data' non trovato nel file HDF5.")
                return

            group = f['normalized_data']
            
            print("Caricamento dati in memoria per ispezione rapida...")
            cached_data = {}
            for _, key, _ in mapping:
                if key in group:
                    cached_data[key] = group[key][:]

            # Inizializzazione della finestra interattiva di Matplotlib
            plt.ion()
            fig, ax = plt.subplots(figsize=(14, 8))
            fig.canvas.manager.set_window_title("WorldEngine Advanced Map Inspector")

            # Impostazione del layer iniziale
            current_key = list(loaded_images.keys())[0]
            current_label, current_img = loaded_images[current_key]
            
            im_plot = ax.imshow(current_img)
            ax.set_title(f"Mappa Corrente: {current_label}\n[Tasti 1-5 per cambiare mappa | Passa il mouse per info | Click per log su Terminale]")

            # Creazione del menù contestuale grafico (Tooltip) all'interno degli assi
            tooltip = ax.text(
                0.02, 0.98, "", 
                transform=ax.transAxes,    
                verticalalignment='top', 
                horizontalalignment='left',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='black', alpha=0.85, edgecolor='gray'),
                color='white', 
                fontsize=9, 
                fontfamily='monospace',
                animated=True # Ottimizzazione rendering per spostamenti veloci
            )
            ax.add_artist(tooltip)

            print("\n" + "="*60)
            print("--- ISPEZIONE VISUALE AVANZATA ATTIVA ---")
            print("= Muovi il mouse sulla mappa: apparirà il menù contestuale.")
            print("= Clicca su un punto per stampare il log completo nel terminale.")
            print("= Usa gli strumenti di Matplotlib per fare Zoom/Pan.")
            print("= Premi i tasti da [1] a [5] sulla mappa per cambiare layer.")
            print("="*60 + "\n")

            # Funzione di helper per formattare la stringa delle info di un pixel
            def get_pixel_info_text(x, y):
                lines = [f"COORDINATE: X={x}, Y={y}", "-" * 30]
                for label, key, unit in mapping:
                    if key in cached_data:
                        val = cached_data[key][y, x]
                        if isinstance(val, bytes):
                            val = val.decode('utf-8')
                        
                        if isinstance(val, (bool, np.bool_)):
                            val_str = "Si" if val else "No"
                        else:
                            val_str = f"{val} {unit}".strip()
                        lines.append(f"{label:<18} : {val_str}")
                    else:
                        lines.append(f"{label:<18} : n/d")
                return "\n".join(lines)

            # Gestione sicura del background per il Blitting senza attributi errati
            bg = None

            def on_draw(event):
                nonlocal bg
                # Cattura in modo sicuro la regione del canvas legata ai nostri assi
                bg = fig.canvas.copy_from_bbox(ax.bbox)

            fig.canvas.mpl_connect('draw_event', on_draw)

            # 1. EVENTO HOVER (Movimento del mouse)
            def on_mouse_move(event):
                nonlocal bg
                if event.xdata is None or event.ydata is None:
                    if tooltip.get_visible():
                        tooltip.set_visible(False)
                        fig.canvas.draw_idle()
                    return

                x, y = int(np.floor(event.xdata)), int(np.floor(event.ydata))
                width, height = current_img.size

                if 0 <= x < width and 0 <= y < height:
                    info_text = get_pixel_info_text(x, y)
                    tooltip.set_text(info_text)
                    tooltip.set_visible(True)
                    
                    # Riposizionamento dinamico del menù per prevenire coperture
                    if event.xdata < width / 2:
                        tooltip.set_transform(ax.transAxes)
                        tooltip.set_position((0.68, 0.96)) 
                    else:
                        tooltip.set_transform(ax.transAxes)
                        tooltip.set_position((0.02, 0.96)) 

                    # Ripristino e disegno rapido sul canvas tramite blit
                    if bg is not None:
                        fig.canvas.restore_region(bg)
                        ax.draw_artist(im_plot)
                        ax.draw_artist(tooltip)
                        fig.canvas.blit(ax.bbox)
                else:
                    if tooltip.get_visible():
                        tooltip.set_visible(False)
                        fig.canvas.draw_idle()

            # 2. EVENTO CLICK (Log persistente su Terminale)
            def on_click(event):
                if event.xdata is None or event.ydata is None:
                    return
                x, y = int(np.floor(event.xdata)), int(np.floor(event.ydata))
                width, height = current_img.size

                if 0 <= x < width and 0 <= y < height:
                    print(f"\n[Log Terminale - Click su Pixel: X={x}, Y={y}]")
                    print("-" * 45)
                    print(get_pixel_info_text(x, y))
                    print("-" * 45)

            # 3. EVENTO CAMBIO LAYER (Tasti 1-5)
            def on_key(event):
                nonlocal current_key, current_label, current_img, bg
                
                if event.key in loaded_images and event.key != current_key:
                    current_key = event.key
                    current_label, current_img = loaded_images[current_key]
                    
                    xlim = ax.get_xlim()
                    ylim = ax.get_ylim()
                    
                    im_plot.set_data(current_img)
                    ax.set_title(f"Mappa Corrente: {current_label}\n[Tasti 1-5 per cambiare mappa | Passa il mouse per info | Click per log su Terminale]")
                    
                    ax.set_xlim(xlim)
                    ax.set_ylim(ylim)
                    
                    # Ridisegna l'intera figura e ricattura la cache dello sfondo
                    tooltip.set_visible(False)
                    fig.canvas.draw()
                    bg = fig.canvas.copy_from_bbox(ax.bbox)
                    print(f"Layer visualizzato: {current_label}")

            # Registrazione dei listener hardware
            fig.canvas.mpl_connect('motion_notify_event', on_mouse_move)
            fig.canvas.mpl_connect('button_press_event', on_click)
            fig.canvas.mpl_connect('key_press_event', on_key)

            plt.show(block=True)
                        
    except Exception as e:
        print(f"Errore generale durante l'estrazione: {e}")

if __name__ == "__main__":
    path = "assets/map/world.world" 
    get_map_data(path)