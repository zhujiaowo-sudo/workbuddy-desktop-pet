"""Check a community ZIP/folder without activating or keeping it."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from workbuddy_pet.materials import MaterialError, MaterialLibrary, iter_animation


def main():
    parser=argparse.ArgumentParser(description='校验桌宠素材包，不启用、不上传')
    parser.add_argument('source',type=Path)
    args=parser.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix='wb-pet-validate-') as temporary:
            pack=MaterialLibrary(Path(temporary)/'library').import_pack(args.source)
            result={}
            for action,item in pack.actions.items():
                count=0;size=None;duration=0
                for frame in iter_animation(pack.root/item.file,long=pack.schema==3):
                    count+=1;size=frame.size;duration+=frame.duration
                result[action]={'frames':count,'size':list(size),'loop':item.loop,'duration_ms':duration}
            print(json.dumps({'valid':True,'schema':pack.schema,'quality':pack.quality,'action_count':len(result),
                'actions':result},ensure_ascii=False,indent=2))
            return 0
    except (OSError,MaterialError) as error:
        print(json.dumps({'valid':False,'error':str(error)},ensure_ascii=False));return 1


if __name__=='__main__':raise SystemExit(main())
