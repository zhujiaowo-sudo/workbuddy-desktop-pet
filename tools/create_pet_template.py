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
from workbuddy_pet.templates import export_default


def main():
    parser=argparse.ArgumentParser(description='生成原创小搭子轻量/高清示例包')
    parser.add_argument('--output',type=Path,default=project/'dist/materials')
    parser.add_argument('--catalog',action='store_true',help='将默认下载清单切回旧CC0机器人示例；不指定时仅导出示例')
    args=parser.parse_args()
    app=QApplication.instance() or QApplication(sys.argv[:1])
    entries={}
    for quality in ('light','hd'):
        path=export_default(args.output/f'xiaodazi-1.0.0-{quality}.zip',quality)
        with path.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
        entries[quality]={'name':path.name,'bytes':path.stat().st_size,'sha256':sha,
            'url':f'https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet/releases/download/v0.2.0/{path.name}'}
    if args.catalog:
        (project/'src/workbuddy_pet/catalog.json').write_text(json.dumps({'schema':1,'packs':entries},indent=2),encoding='utf-8')
    print(json.dumps(entries,indent=2))


if __name__=='__main__':main()
