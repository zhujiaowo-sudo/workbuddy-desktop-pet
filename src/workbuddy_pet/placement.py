"""Place the companion window without moving the pet itself."""
from .settings import Rect, clamp_position


def fit_capsule_pet(pet: Rect,size: tuple[int,int],screens):
    """Reserve room above and on both sides, moving the pair together at edges."""
    if not screens:return (pet.x,pet.y)
    center=(pet.x+pet.width/2,pet.y+pet.height/2)
    screen=min(screens,key=lambda s:max(s.x-center[0],0,center[0]-s.x-s.width)**2+
               max(s.y-center[1],0,center[1]-s.y-s.height)**2)
    width,height=size
    inset=max(0,(width-pet.width)/2)
    low_x=screen.x+inset;high_x=screen.x+screen.width-pet.width-inset
    low_y=screen.y+height+8;high_y=screen.y+screen.height-pet.height
    x=round(max(low_x,min(pet.x,high_x))) if low_x<=high_x else pet.x
    y=max(low_y,min(pet.y,high_y)) if low_y<=high_y else pet.y
    return clamp_position((x,y),(pet.width,pet.height),[screen])


def card_position(pet: Rect, size: tuple[int,int], screens, *, compact: bool):
    if not screens:return (0,0)
    center=(pet.x+pet.width/2,pet.y+pet.height/2)
    screen=min(screens,key=lambda s:max(s.x-center[0],0,center[0]-s.x-s.width)**2+
               max(s.y-center[1],0,center[1]-s.y-s.height)**2)
    width,height=size
    if compact:
        x=round(center[0]-width/2);y=pet.y-height-8
        if y<screen.y:y=pet.y+pet.height+8
    else:
        left=pet.x-width-8;right=pet.x+pet.width+8
        x=left if left>=screen.x else right;y=pet.y+pet.height-height
    return clamp_position((x,y),size,[screen])
