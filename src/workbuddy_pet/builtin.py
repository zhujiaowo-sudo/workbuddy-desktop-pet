"""The single bundled, offline animated character set."""
from pathlib import Path
from .materials import validate_pack

PACK_ROOT=Path(__file__).with_name('assets')/'default_pet'

def builtin_pack():
    return validate_pack(PACK_ROOT,decode=False,key='builtin')
