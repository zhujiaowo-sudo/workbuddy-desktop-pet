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


def test_visible_anchor_skips_window_and_canvas_padding():
    pet=Rect(900,650,248,297);anchor=Rect(970,730,110,190)
    x,y=card_position(pet,(272,32),[Rect(0,0,1920,1040)],compact=True,anchor=anchor)
    assert y+32==anchor.y-8 and abs(x+136-(anchor.x+55))<=1
    assert y>pet.y


def test_visible_anchor_and_full_window_both_stay_on_screen():
    for screen in (Rect(0,0,1920,1040),Rect(-1920,0,1920,1040)):
        for x,y in ((screen.x,0),(screen.x+1672,743),(screen.x+900,0)):
            pet=Rect(x,y,248,297);anchor=Rect(x+31,y+118,97,110)
            fitted=fit_capsule_pet(pet,(272,32),[screen],anchor=anchor)
            window=Rect(*fitted,248,297)
            visible=Rect(fitted[0]+31,fitted[1]+118,97,110)
            cx,cy=card_position(window,(272,32),[screen],compact=True,anchor=visible)
            assert window.x>=screen.x and window.x+248<=screen.x+screen.width and 0<=window.y<=743
            assert cx>=screen.x and cx+272<=screen.x+screen.width and cy>=screen.y
            assert cy+32==visible.y-8 and abs(cx+136-(visible.x+visible.width/2))<=1
