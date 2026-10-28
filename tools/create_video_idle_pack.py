"""Package the approved video-idle derivative; preserve all legacy action content."""
import argparse,hashlib,io,json,sys,zipfile
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from workbuddy_pet.materials import iter_animation,alpha_bounds,validate_pack
from workbuddy_pet.rig_export import save_apng

def main():
 p=argparse.ArgumentParser();p.add_argument('--legacy',type=Path,required=True);p.add_argument('--idle-master',type=Path,required=True);p.add_argument('--idle-light',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--catalog',type=Path,required=True);args=p.parse_args()
 args.output.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(args.legacy) as z:
  source=json.loads(z.read('manifest.json'));legacy={n:z.read(n) for n in z.namelist() if n!='manifest.json'}
 import tempfile
 entries={}
 with tempfile.TemporaryDirectory(prefix='wb-publish-material-') as tmp:
  root=Path(tmp)
  for n,data in legacy.items():
   q=root/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
  for quality,size in (('light',512),('hd',720)):
   manifest=json.loads(json.dumps(source));payload={};bounds=[]
   manifest.update(schema=3,id='mint-orbit-interactive',name='薄荷星伴 · 视频待机版',version='1.5.0',quality=quality)
   for action,definition in manifest['actions'].items():
    n=definition['file']
    if action=='idle':
     n='actions/idle.webp' if quality=='light' else 'actions/idle.png';definition['file']=n
     blob=(args.idle_light if quality=='light' else args.idle_master).read_bytes()
    elif quality=='light':blob=legacy[n]
    else:
     decoded=list(iter_animation(root/n));frames=[]
     for frame in decoded:
      im=Image.frombytes('RGBA',frame.size,frame.rgba).convert('RGBa').resize((720,720),Image.Resampling.LANCZOS).convert('RGBA');frames.append(im)
     stream=io.BytesIO()
     if n.endswith('.png'):save_apng(frames,stream,[f.duration for f in decoded])
     else:frames[0].save(stream,format='WEBP',save_all=True,append_images=frames[1:],duration=[f.duration for f in decoded],loop=0,lossless=True,method=4)
     blob=stream.getvalue()
    payload[n]=blob
    path=root/quality/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
    bounds.extend(f.bounds for f in iter_animation(path,long=True))
   manifest['anchor']=[min(b[0] for b in bounds),min(b[1] for b in bounds),max(b[2] for b in bounds),max(b[3] for b in bounds)]
   manifest['files']={n:hashlib.sha256(blob).hexdigest() for n,blob in payload.items()}
   manifest['source']['changes']='仅idle改为用户提供AI视频的正向原帧：头盔特征尺度稳定、脚底注册、白底透明处理和选段，80帧/3333ms；未倒放或整图淡化。其他15段沿用1.4.0：512档文件字节不变，720档由512画布统一预乘Alpha缩放，不增加原画细节。首尾嘴型及局部细节仍有差异，不宣称完全无缝；其他动作未重制。'
   manifest['source']['video_sha256']='26a26138036bd836d1c5fe8bb265a31e020b6643be0d36a6a413da593a9e5bcf'
   manifest['source']['ai_generated']=True
   text=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8');(root/quality/'manifest.json').write_bytes(text)
   validate_pack(root/quality)
   name=f'mint-orbit-interactive-{quality}-v1.5.0.zip';target=args.output/name
   with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('manifest.json',text)
    for n,blob in payload.items():z.writestr(n,blob)
   entries[quality]={'name':name,'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'url':f'https://github.com/zhujiaowo-sudo/workbuddy-desktop-pet/releases/download/v0.6.3/{name}'}
   assert entries[quality]['bytes']<128*1024*1024
   print(json.dumps({quality:entries[quality]},ensure_ascii=True),flush=True)
 args.catalog.write_text(json.dumps({'schema':1,'release':'v0.6.3','packs':entries},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
