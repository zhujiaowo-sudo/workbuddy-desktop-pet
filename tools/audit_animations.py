"""Export every frame/loop and verify the actual player's time sampling."""
import argparse,hashlib,json,os,sys,tempfile,time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
project=Path(__file__).resolve().parents[1];sys.path.insert(0,str(project/'src'))
from PIL import Image,ImageDraw
from PySide6.QtWidgets import QApplication
from workbuddy_pet.materials import MaterialLibrary,decode_animation
from workbuddy_pet.ui.animation import AnimationPlayer
from workbuddy_pet.rig_export import save_apng,cutout_animations


def main():
    parser=argparse.ArgumentParser();parser.add_argument('pack',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    app=QApplication.instance() or QApplication([]);player=AnimationPlayer()
    report={'sampling':'controlled_monotonic_timestamps','actions':[],'source_sha256':hashlib.sha256(args.pack.read_bytes()).hexdigest()}
    with tempfile.TemporaryDirectory() as temporary:
        pack=MaterialLibrary(Path(temporary)/'library').import_pack(args.pack)
        for action,definition in pack.actions.items():
            frames=decode_animation(pack.root/definition.file)
            images=[Image.frombytes('RGBA',f.size,f.rgba) for f in frames]
            sheet=Image.new('RGBA',(768,208*((len(frames)+3)//4)),(240,246,250,255));draw=ImageDraw.Draw(sheet)
            for index,frame in enumerate(images):
                sheet.alpha_composite(frame.resize((192,192),Image.Resampling.LANCZOS),((index%4)*192,(index//4)*208))
                draw.text(((index%4)*192+8,(index//4)*208+190),f'{index+1} / {frames[index].duration}ms',fill='#284b66')
            sheet.convert('RGB').save(args.output/(action+'-frames.png'))
            with (args.output/(action+'-loop.png')).open('wb') as stream:save_apng(images,stream,[f.duration for f in frames])
            player.load(pack,action);samples=0
            for index in range(len(frames)):
                assert player.index==index
                expected=player.frames[index][0].cacheKey()
                for fraction in (0,.25,.5,.75,.99):
                    player.frame_started=time.monotonic()-frames[index].duration/1000*fraction
                    assert player.pixmap.cacheKey()==expected,(action,index,fraction)
                    samples+=1
                player.advance()
            assert player.index==(0 if definition.loop else len(frames)-1)
            report['actions'].append({'action':action,'frames':len(frames),'ms':sum(f.duration for f in frames),'samples_without_blending':samples,'loop':definition.loop})
        if 'idle_scratch' in pack.actions:
            resolution=256 if pack.quality=='light' else 512
            expected=cutout_animations(project/'art/mint-orbit/rig-kit-v1.4.0.png',resolution)
            combined=[];durations=[]
            for name,original in zip(('idle','idle_scratch'),expected):
                decoded=decode_animation(pack.root/pack.actions[name].file)
                assert all(f.rgba==image.tobytes() for f,image in zip(decoded,original))
                combined.extend(original);durations.extend(f.duration for f in decoded)
            with (args.output/'idle-scratch-replay.png').open('wb') as stream:save_apng(combined,stream,durations)
            report['canonical_rig_roundtrip']=True
    player.clear()
    (args.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'actions':len(report['actions']),'render_samples':sum(a['samples_without_blending'] for a in report['actions']),
        'canonical_rig_roundtrip':report.get('canonical_rig_roundtrip',False),'output':str(args.output)}),flush=True)


if __name__=='__main__':main()
