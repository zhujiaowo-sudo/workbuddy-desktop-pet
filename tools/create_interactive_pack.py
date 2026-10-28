"""Generate original templates and attributed Mint derivatives; no account access."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
project=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(project/'src'))
from PySide6.QtWidgets import QApplication
from workbuddy_pet.interactive_export import export_interactive
from workbuddy_pet.materials import MaterialLibrary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,help='用户原始素材包；省略时导出CC0机器人模板')
    parser.add_argument('--typing-sheet',type=Path,help='4列2行坐姿打字透明精灵图')
    parser.add_argument('--output',type=Path,default=project/'dist/materials')
    parser.add_argument('--catalog',action='store_true')
    args=parser.parse_args()
    if args.source and args.typing_sheet is None:
        args.typing_sheet=project/'art/mint-orbit/typing-sheet-v1.1.1.png'
    app=QApplication.instance() or QApplication(sys.argv[:1])
    entries={}
    for quality in ('light','hd'):
        name=f'mint-orbit-interactive-{quality}-v1.2.0.zip' if args.source else f'workbuddy-pet-template-{quality}-v2.0.1.zip'
        leisure={f'leisure_{key}':project/f'art/mint-orbit/{key}-sheet-v1.2.0.png' for key in ('phone','snack')} if args.source else None
        path=export_interactive(args.output/name,quality,args.source,args.typing_sheet,leisure)
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            pack=MaterialLibrary(Path(temporary)/'library').import_pack(path)
            assert pack.schema==2 and len(pack.actions)==15
        entries[quality]={'name':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'url':f'https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet/releases/download/v0.6.0/{name}'}
        print(json.dumps({quality:entries[quality]},ensure_ascii=True),flush=True)
    if args.catalog:
        if not args.source:raise ValueError('默认清单只可由明确指定的薄荷源包更新')
        (project/'src/workbuddy_pet/catalog.json').write_text(json.dumps({'schema':1,'release':'v0.6.0','packs':entries},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
