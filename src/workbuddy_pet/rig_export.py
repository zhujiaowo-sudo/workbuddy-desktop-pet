"""Assemble authored cutout layers with rigid joints, never blend whole poses."""
import math
from PIL import Image,ImageDraw

from .materials import alpha_bounds
from .sprite_sheet import _remove_specks


def _crop_part(sheet,col,top,bottom):
    width=sheet.width/3
    part=_remove_specks(sheet.crop((round(col*width),round(top*sheet.height),round((col+1)*width),round(bottom*sheet.height))))
    return part.crop(alpha_bounds(part))


def rig_layers(sheet_path,resolution):
    with Image.open(sheet_path) as source:
        sheet=source.convert('RGBA')
        bodies=[_crop_part(sheet,col,0,.66) for col in range(3)]
        upper,fore,glove=[_crop_part(sheet,col,.68,1) for col in range(3)]
    base_source=bodies[0]
    scale=min(resolution*.78/base_source.height,resolution*.81/base_source.width)
    size=(round(base_source.width*scale),round(base_source.height*scale))
    base=Image.new('RGBA',(resolution,resolution))
    origin=((resolution-size[0])//2,round(resolution*.9)-size[1])
    base.alpha_composite(base_source.resize(size,Image.Resampling.LANCZOS),origin)
    box=alpha_bounds(base);x,y,right,bottom=box;w,h=right-x,bottom-y
    eyes=[]
    for body in bodies:
        head=body.crop((0,0,body.width,round(body.height*.445)))
        bounds=alpha_bounds(head);head=head.crop(bounds)
        reference_head=base_source.crop((0,0,base_source.width,round(base_source.height*.445)))
        ref_bounds=alpha_bounds(reference_head)
        registered=Image.new('RGBA',base.size)
        target=(round((ref_bounds[2]-ref_bounds[0])*scale),round((ref_bounds[3]-ref_bounds[1])*scale))
        registered.alpha_composite(head.resize(target,Image.Resampling.LANCZOS),
            (origin[0]+round(ref_bounds[0]*scale),origin[1]+round(ref_bounds[1]*scale)))
        face=base.copy()
        # Only the two eye panels change. Nose, mouth, hair silhouette and all
        # lower-body pixels always come from the same canonical base.
        for left,right_edge in ((.25,.49),(.50,.76)):
            region=(round(x+w*left),round(y+h*.275),round(x+w*right_edge),round(y+h*.365))
            face.paste(registered.crop(region),region)
        eyes.append(face)
    eyes[0]=base.copy()
    return tuple(eyes),(upper,fore,glove),box


def _attach(canvas,part,anchor,length,angle,width=None):
    scale=length/part.height
    resized=part.resize((max(1,round(width if width is not None else part.width*scale)),max(1,round(length))),Image.Resampling.LANCZOS)
    side=math.ceil(length*3+16);center=side//2
    layer=Image.new('RGBA',(side,side))
    layer.alpha_composite(resized,(center-resized.width//2,center-round(resized.height*.04)))
    rotated=layer.rotate(90-angle,resample=Image.Resampling.BICUBIC,center=(center,center))
    canvas.alpha_composite(rotated,(round(anchor[0])-center,round(anchor[1])-center))


def arm_pose(index):
    # Smooth joint positions are real geometry; no opacity mixture of poses.
    progress=(0,.08,.30,.65,1,1,1,1,1,1,.90,.70,.45,.22,.06,0)[index]
    eased=progress*progress*(3-2*progress)
    rub=(0,0,0,0,0,-5,5,-5,5,0,0,0,0,0,0,0)[index]
    return 120+70*eased,110+160*eased+rub


def rig_frame(eyes,parts,box,angles,expression=0):
    image=Image.new('RGBA',eyes[expression].size);upper,fore,glove=parts
    x,y,right,bottom=box;w,h=right-x,bottom-y
    shoulder=(x+w*.35,y+h*.45);upper_length=h*.10;fore_length=h*.09
    a,b=angles
    elbow=(shoulder[0]+math.cos(math.radians(a))*upper_length,shoulder[1]+math.sin(math.radians(a))*upper_length)
    wrist=(elbow[0]+math.cos(math.radians(b))*fore_length,elbow[1]+math.sin(math.radians(b))*fore_length)
    _attach(image,upper,shoulder,upper_length+h*.025,a,w*.115)
    image.alpha_composite(eyes[expression])
    _attach(image,fore,elbow,fore_length+h*.025,b,w*.115)
    _attach(image,glove,wrist,h*.105,b)
    return image


def cutout_animations(sheet_path,resolution):
    eyes,parts,box=rig_layers(sheet_path,resolution)
    rest=arm_pose(0)
    idle=tuple(rig_frame(eyes,parts,box,rest,expression) for expression in ([0]*12+[1,2,1,0]))
    scratch=tuple(rig_frame(eyes,parts,box,arm_pose(index),2 if 5<=index<=9 else 0) for index in range(16))
    return idle,scratch


def save_apng(frames,stream,durations):
    # Alternate disposal modes with SOURCE painting, preserving identical hold
    # frames instead of merging them into a duration above the pack's 200ms cap.
    frames[0].save(stream,format='PNG',save_all=True,append_images=frames[1:],duration=durations,
                   loop=0,disposal=[0 if i%2==0 else 2 for i in range(len(frames))],blend=0,optimize=False)
