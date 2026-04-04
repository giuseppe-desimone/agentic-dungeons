"""Script di avvio per il sistema GDR v0.8.

Uso:
    python run.py
"""

import io
import sys

# Forza UTF-8 su Windows per supportare caratteri italiani (à, é, ì, ecc.)
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")
if isinstance(sys.stderr, io.TextIOWrapper):
    sys.stderr.reconfigure(encoding="utf-8")

from app.main import main

if __name__ == "__main__":
    main()
