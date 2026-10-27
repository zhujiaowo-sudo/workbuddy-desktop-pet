from workbuddy_pet.settings import Rect
from workbuddy_pet.placement import card_position,fit_capsule_pet


def test_capsule_is_centered_above_pet_for_each_size():
    for size in (100,160,240):
        pet=Rect(900,650,size+24,int(size*1.22)+24)
        x,y=card_position(pet,(272,32),[Rect(0,0,1920,1040)],compact=True)
        assert abs(x+136-(pet.x+pet.width/2))<=1
        assert y+32==pet.y-8


def test_expanded_card_and_screen_edge_never_cover_pet():
    screen=Rect(0,0,1920,1040)
    pet=Rect(1600,700,124,146)
    x,y=card_position(pet,(360,540),[screen],compact=False)
    assert x+360==pet.x-8 and y+540==pet.y+pet.height
    pet=Rect(0,0,124,146)
    x,y=card_position(pet,(272,32),[screen],compact=True)
    assert x>=0 and y>=pet.y+pet.height
    x,y=card_position(pet,(360,540),[screen],compact=False)
    assert x>=pet.x+pet.width and y>=0


def test_secondary_screen_and_bottom_edge():
    screens=[Rect(-1920,0,1920,1040),Rect(0,0,1920,1040)]
    pet=Rect(-500,860,184,219)
    x,y=card_position(pet,(272,32),screens,compact=True)
    assert -1920<=x and x+272<=0 and y+32<=1040


def test_capsule_and_pet_move_together_at_edges():
    screen=Rect(0,0,1920,1040)
    for x,y in ((1796,800),(0,0),(900,0)):
        pet=Rect(x,y,124,146)
        anchor=fit_capsule_pet(pet,(272,32),[screen])
        fitted=Rect(*anchor,pet.width,pet.height)
        cx,cy=card_position(fitted,(272,32),[screen],compact=True)
        assert abs(cx+136-(fitted.x+62))<=1
        assert cy+32==fitted.y-8
        assert cx>=0 and cx+272<=1920 and cy>=0
