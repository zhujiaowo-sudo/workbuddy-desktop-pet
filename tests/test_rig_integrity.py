import io
from pathlib import Path
from PIL import Image

from workbuddy_pet.rig_export import cutout_animations,rig_layers,save_apng
from workbuddy_pet.materials import decode_animation

KIT=Path(__file__).resolve().parents[1]/'art/mint-orbit/rig-kit-v1.4.0.png'


def test_idle_and_scratch_share_identical_legs_head_outline_and_mouth():
    idle,scratch=cutout_animations(KIT,256);eyes,parts,box=rig_layers(KIT,256)
    x,y,right,bottom=box;w,h=right-x,bottom-y
    regions=((round(x+w*.32),round(y+h*.65),round(x+w*.72),bottom),
        (0,0,256,round(y+h*.21)),
        (round(x+w*.40),round(y+h*.38),round(x+w*.65),round(y+h*.43)))
    for region in regions:
        canonical=idle[0].crop(region).tobytes()
        assert all(frame.crop(region).tobytes()==canonical for frame in idle+scratch)
    # The hand may touch the helmet, but must not cover the eyes themselves.
    for index,frame in enumerate(scratch):
        expected=eyes[2 if 5<=index<=9 else 0]
        for left,right_edge in ((.32,.47),(.55,.70)):
            region=(round(x+w*left),round(y+h*.285),round(x+w*right_edge),round(y+h*.36))
            assert frame.crop(region).tobytes()==expected.crop(region).tobytes()


def test_arm_hand_scale_matches_the_attached_reference_hand():
    idle,_=cutout_animations(KIT,512);_,_,box=rig_layers(KIT,512)
    x,y,right,bottom=box;w,h=right-x,bottom-y
    def width(left,right_edge):
        crop=idle[0].crop((round(x+w*left),round(y+h*.66),round(x+w*right_edge),round(y+h*.76)))
        mask=Image.new('L',crop.size)
        pixels=list(crop.get_flattened_data())
        selected=bytearray(1 if a>220 and min(r,g,b)>210 and max(r,g,b)-min(r,g,b)<40 else 0 for r,g,b,a in pixels)
        components=[]
        for start in range(len(selected)):
            if not selected[start]:continue
            selected[start]=0;queue=[start]
            for index in queue:
                xx,yy=index%crop.width,index//crop.width
                for neighbour in (index-1 if xx else -1,index+1 if xx+1<crop.width else -1,index-crop.width if yy else -1,index+crop.width if yy+1<crop.height else -1):
                    if neighbour>=0 and selected[neighbour]:selected[neighbour]=0;queue.append(neighbour)
            components.append(queue)
        largest=max(components,key=len)
        return max(i%crop.width for i in largest)-min(i%crop.width for i in largest)+1
    ratio=width(.02,.36)/width(.72,1.03)
    assert .75<=ratio<=1.25


def test_apng_retains_exact_hold_frames_without_blending_or_long_durations(tmp_path):
    idle,scratch=cutout_animations(KIT,256)
    for name,frames,durations in (('idle',idle,[200]*12+[80,80,80,200]),('scratch',scratch,[100]*16)):
        buffer=io.BytesIO();save_apng(frames,buffer,durations)
        path=tmp_path/(name+'.png');path.write_bytes(buffer.getvalue())
        decoded=decode_animation(path)
        assert len(decoded)==16 and [f.duration for f in decoded]==durations
        assert all(frame.rgba==original.tobytes() for frame,original in zip(decoded,frames))
    assert all(frame.tobytes()==idle[0].tobytes() for frame in idle[:12])
