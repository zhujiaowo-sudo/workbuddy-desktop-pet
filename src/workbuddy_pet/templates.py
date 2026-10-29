"""Export a byte-preserving copy of the bundled character with attribution."""
from pathlib import Path
import zipfile
from .builtin import builtin_pack

def export_starter(destination: Path,key='builtin'):
    PACK_ROOT=builtin_pack(key).root
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PACK_ROOT.rglob('*')):
            if path.is_file():archive.write(path,path.relative_to(PACK_ROOT).as_posix())
    return destination

def export_default(destination: Path,quality='hd'):
    return export_starter(destination)
