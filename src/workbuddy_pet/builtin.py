"""Bundled offline character sets; existing default identity remains stable."""
from pathlib import Path
from .materials import validate_pack,MaterialError
PACK_ROOT=Path(__file__).with_name('assets')/'default_pet'
BUILTIN_PACKS={'builtin':PACK_ROOT,'builtin-blue-fish':PACK_ROOT.parent/'blue_fish'}
def builtin_pack(key='builtin'):
    if key not in BUILTIN_PACKS:raise MaterialError('未知内置角色')
    return validate_pack(BUILTIN_PACKS[key],decode=False,key=key)
