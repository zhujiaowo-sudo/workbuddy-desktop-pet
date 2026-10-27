"""Source-tree entry point; frozen builds use this same dispatcher."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from workbuddy_pet.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
