#!/usr/bin/env python3
"""
img2ascii — Visualizzatore di immagini nel terminale con pixel quadrati (mezzo blocco ANSI TrueColor).

Utilizza il carattere '▀' (\u2580):
- Metà superiore colorata con il colore di primo piano (foreground ANSI)
- Metà inferiore colorata con il colore di sfondo (background ANSI)
Ogni cella ospita due sub-pixel verticali con proporzioni 1:1 (quadrati).

Esempi:
    python src/img2ascii.py assets/images/OIP-2146877812.jpg
    python src/img2ascii.py assets/images/OIP-2146877812.jpg -c 120
"""

import argparse
import sys
from PIL import Image

_RESET = "\x1b[0m"
_DEFAULT_COLS = 150


def render_image(image_path: str, cols: int = _DEFAULT_COLS) -> str:
    """Converte un'immagine in formato testo ANSI TrueColor usando caratteri mezzo blocco '▀'."""
    img = Image.open(image_path).convert("RGB")
    width, height = img.size

    # Una cella monospace nel terminale ha una proporzione ~1:2 (larghezza:altezza).
    # Con il mezzo blocco '▀' ogni cella ospita 2 pixel verticali, rendendo
    # ciascun pixel geometricamente quadrato (~1:1).
    pixel_width = cols
    pixel_height = max(1, int(round(height * (cols / width))))

    resample = getattr(Image.Resampling, "BOX", Image.BOX)
    img = img.resize((pixel_width, pixel_height), resample)

    data = img.tobytes()  # Dati raw RGB (3 byte per pixel)
    lines = []
    terminal_rows = (pixel_height + 1) // 2

    for r in range(terminal_rows):
        y_top = r * 2
        y_bot = y_top + 1
        has_bot = y_bot < pixel_height

        top_base = y_top * pixel_width * 3
        bot_base = y_bot * pixel_width * 3 if has_bot else 0

        row = []
        for x in range(pixel_width):
            off_t = top_base + x * 3
            rt, gt, bt = data[off_t], data[off_t + 1], data[off_t + 2]

            if has_bot:
                off_b = bot_base + x * 3
                rb, gb, bb = data[off_b], data[off_b + 1], data[off_b + 2]
                row.append(f"\x1b[38;2;{rt};{gt};{bt}m\x1b[48;2;{rb};{gb};{bb}m▀")
            else:
                row.append(f"\x1b[38;2;{rt};{gt};{bt}m\x1b[49m▀")

        lines.append("".join(row) + _RESET)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Visualizza un'immagine a colori nel terminale tramite mezzi blocchi ANSI TrueColor."
    )
    parser.add_argument(
        "image",
        help="Percorso dell'immagine da visualizzare",
    )
    parser.add_argument(
        "-c", "--cols",
        type=int,
        default=_DEFAULT_COLS,
        help=f"Larghezza in colonne/caratteri (default: {_DEFAULT_COLS})",
    )

    args = parser.parse_args()

    try:
        sys.stdout.write(render_image(args.image, cols=args.cols) + "\n")
    except FileNotFoundError:
        sys.exit(f"Errore: immagine non trovata: {args.image}")
    except Image.UnidentifiedImageError:
        sys.exit(f"Errore: il file indicato non è un'immagine valida: {args.image}")


if __name__ == "__main__":
    main()
