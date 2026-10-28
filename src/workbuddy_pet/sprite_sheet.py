"""Technical extraction/registration of generated typing keyframes, no account data."""
from PIL import Image, ImageDraw, ImageFilter

from .materials import alpha_bounds


def _remove_specks(image):
    alpha=bytearray(image.getchannel('A').tobytes());width,height=image.size
    seen=bytearray(len(alpha));components=[]
    for start,value in enumerate(alpha):
        if seen[start] or value<=16:continue
        seen[start]=1;queue=[start]
        for index in queue:
            x,y=index%width,index//width
            for next_index in ((index-1 if x else -1),(index+1 if x+1<width else -1),
                               (index-width if y else -1),(index+width if y+1<height else -1)):
                if next_index>=0 and not seen[next_index] and alpha[next_index]>16:
                    seen[next_index]=1;queue.append(next_index)
        components.append(queue)
    if not components:raise ValueError('打字精灵帧为空')
    keep=max(components,key=len)
    cleaned=bytearray(len(alpha))
    for component in components:
        if component is keep or len(component)>=64:
            for index in component:cleaned[index]=alpha[index]
    output=image.copy();output.putalpha(Image.frombytes('L',image.size,bytes(cleaned)))
    return output


def typing_frames(sheet_path,resolution,*,regions=((.23,.25,.57,.46),(.29,.52,.60,.68))):
    """4x2 sheet: lock furniture/outline, animate only registered face and hands."""
    with Image.open(sheet_path) as sheet:
        sheet=sheet.convert('RGBA');raw=[]
        for row in range(2):
            for col in range(4):
                box=(round(col*sheet.width/4),round(row*sheet.height/2),
                     round((col+1)*sheet.width/4),round((row+1)*sheet.height/2))
                raw.append(_remove_specks(sheet.crop(box)))
    bounds=[alpha_bounds(frame) for frame in raw]
    scale=min(resolution*.78/max(b[3]-b[1] for b in bounds),
              resolution*.81/max(b[2]-b[0] for b in bounds))
    ref=bounds[0];center=(ref[0]+ref[2])/2;baseline=ref[3]
    frames=[]
    # Register the bottom band: furniture/feet, rather than moving eyes/hands.
    band=round(raw[0].height*.72)
    def anchor(image):
        box=image.getchannel('A').crop((0,band,image.width,image.height)).getbbox()
        return box[0],band+box[3]
    reference=anchor(raw[0])
    for image in raw:
        left,bottom=anchor(image)
        resized=image.resize((round(image.width*scale),round(image.height*scale)),Image.Resampling.LANCZOS)
        canvas=Image.new('RGBA',(resolution,resolution))
        x=round(resolution/2-center*scale+(reference[0]-left)*scale)
        y=round(resolution*.9-baseline*scale+(reference[1]-bottom)*scale)
        canvas.alpha_composite(resized,(x,y));frames.append(canvas)
    base=frames[0];box=alpha_bounds(base);x,y,right,bottom=box;w,h=right-x,bottom-y
    mask=Image.new('L',base.size);draw=ImageDraw.Draw(mask)
    # Eyes/cheeks and wrists/keyboard. Desk, monitor and silhouette remain exact.
    for a,b,c,d in regions:
        draw.rounded_rectangle((round(x+w*a),round(y+h*b),round(x+w*c),round(y+h*d)),radius=3,fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(max(.7,resolution/340)))
    return tuple(Image.composite(frame,base,mask) for frame in frames)


def leisure_frames(sheet_path,resolution):
    """Seated phone/snack: fixed chair, boots and silhouette; face/forearms move."""
    return typing_frames(sheet_path,resolution,regions=((.23,.29,.74,.54),(.25,.48,.76,.73)))


def gentle_idle_frames(sheet_path,resolution):
    """One blink per 3.2s; quiet open-eye expressions occupy most of the loop."""
    frames=typing_frames(sheet_path,resolution,regions=((.22,.26,.79,.44),))
    quiet=[Image.blend(frames[0],frames[6],index/80) for index in range(11)]
    return tuple(quiet+[frames[1],frames[2],frames[3],frames[4],frames[7]])


def scratch_frames(sheet_path,resolution):
    """The moving arm replaces its resting position, with no duplicate glove."""
    # Preserve the whole authored upper-body pose; a rectangular wrist patch
    # crossing the helmet silhouette leaves a clipped double edge. Feet and
    # lower legs remain registered to the base, without any window movement.
    return typing_frames(sheet_path,resolution,regions=((-.08,-.02,1.08,.78),))
