"""Add src/ ao sys.path para os testes — evita precisar de PYTHONPATH=src."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
