"""Configurazione pytest: aggiunge src/ al sys.path per imports diretti."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
