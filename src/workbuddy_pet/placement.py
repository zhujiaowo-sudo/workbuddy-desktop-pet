"""Place the companion window without moving the pet itself."""
from .settings import Rect, clamp_position


def fit_capsule_pet(pet: Rect,size: tuple[int,int],screens,*,anchor: Rect | None=None):
    """Reserve room above and on both sides, moving the pair together at edges."""
    if not screens:return (pet.x,pet.y)
    center=(pet.x+pet.width/2,pet.y+pet.height/2)
    screen=min(screens,key=lambda s:max(s.x-center[0],0,center[0]-s.x-s.width)**2+
               max(s.y-center[1],0,center[1]-s.y-s.height)**2)
    width,height=size
    anchor=anchor or pet
    center_offset=anchor.x+anchor.width/2-pet.x;top_offset=anchor.y-pet.y
    low_x=max(screen.x,screen.x+width/2-center_offset)
    high_x=min(screen.x+screen.width-pet.width,screen.x+screen.width-width/2-center_offset)
    low_y=max(screen.y,screen.y+height+8-top_offset);high_y=screen.y+screen.height-pet.height
    x=round(max(low_x,min(pet.x,high_x))) if low_x<=high_x else pet.x
    y=max(low_y,min(pet.y,high_y)) if low_y<=high_y else pet.y
    return clamp_position((x,y),(pet.width,pet.height),[screen])


def panel_height_limit(pet: Rect,anchor: Rect,screens):
    if not screens:return 540
    center=(pet.x+pet.width/2,pet.y+pet.height/2)
    screen=min(screens,key=lambda s:max(s.x-center[0],0,center[0]-s.x-s.width)**2+
               max(s.y-center[1],0,center[1]-s.y-s.height)**2)
    return max(0,screen.height-pet.height+anchor.y-pet.y-8)


def card_position(pet: Rect, size: tuple[int,int], screens, *, compact: bool,anchor: Rect | None=None):
    if not screens:return (0,0)
    center=(pet.x+pet.width/2,pet.y+pet.height/2)
    screen=min(screens,key=lambda s:max(s.x-center[0],0,center[0]-s.x-s.width)**2+
               max(s.y-center[1],0,center[1]-s.y-s.height)**2)
    width,height=size
    anchor=anchor or pet
    x=round(anchor.x+anchor.width/2-width/2);y=anchor.y-height-8
    return clamp_position((x,y),size,[screen])


def pet_below_capsule(pet: Rect,anchor: Rect,capsule: Rect,screens):
    """Restore around the detached capsule, then move the whole pair into view."""
    dx,dy=anchor.x-pet.x,anchor.y-pet.y
    x=round(capsule.x+capsule.width/2-dx-anchor.width/2)
    y=capsule.y+capsule.height+8-dy
    candidate=Rect(x,y,pet.width,pet.height)
    visible=Rect(x+dx,y+dy,anchor.width,anchor.height)
    if screens:
        cx,cy=capsule.x+capsule.width/2,capsule.y+capsule.height/2
        screen=min(screens,key=lambda s:max(s.x-cx,0,cx-s.x-s.width)**2+max(s.y-cy,0,cy-s.y-s.height)**2)
        screens=[screen]
    return fit_capsule_pet(candidate,(capsule.width,capsule.height),screens,anchor=visible)
