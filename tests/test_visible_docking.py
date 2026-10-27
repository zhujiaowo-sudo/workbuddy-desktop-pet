import json
from PIL import Image,ImageDraw
from workbuddy_pet.materials import MaterialLibrary,decode_animation
from workbuddy_pet.ui.animation import AnimationPlayer
from workbuddy_pet.ui.pet import PetWindow


def animated_pack(root):
    root.mkdir()
    frames=[]
    for box in ((10,20,29,45),(8,18,32,45)):
        image=Image.new('RGBA',(64,64),(0,255,0,0))
        ImageDraw.Draw(image).rectangle(box,fill=(40,120,220,255));image.putpixel((0,0),(255,0,0,1))
        frames.append(image)
    frames[0].save(root/'idle.webp',save_all=True,append_images=frames[1:],duration=100,lossless=True)
    (root/'manifest.json').write_text(json.dumps({'schema':1,'id':'s','name':'s','author':'s','version':'1',
        'license':'CC0-1.0','quality':'light','actions':{'idle':{'file':'idle.webp'}}}))
    return root


def test_alpha_bounds_ignore_hidden_rgb_and_faint_pixels(tmp_path):
    source=animated_pack(tmp_path/'source')
    frames=decode_animation(source/'idle.webp')
    assert frames[0].bounds==(10,20,30,46) and frames[1].bounds==(8,18,33,46)


def test_animation_uses_stable_union_and_notifies_only_on_load(tmp_path,qt_app):
    pack=MaterialLibrary(tmp_path/'library').import_pack(animated_pack(tmp_path/'source'))
    player=AnimationPlayer();changes=[];player.bounds_changed.connect(lambda:changes.append(player.content_bounds))
    player.load(pack,'idle');player.set_visible(False)
    assert player.content_bounds==(8,18,33,46) and len(changes)==1
    for _ in range(5):
        player.advance();assert player.content_bounds==(8,18,33,46)
    assert len(changes)==1
    player.clear();assert player.content_bounds is None and len(changes)==2


def test_scaled_visual_anchor_matches_rendered_image(tmp_path,qt_app):
    pack=MaterialLibrary(tmp_path/'library').import_pack(animated_pack(tmp_path/'source'))
    player=AnimationPlayer();player.load(pack,'idle');player.set_visible(False)
    pet=PetWindow(size=224);pet.player=player
    assert pet.image_target_rect(player.pixmap).getRect()==(0,49,248,248)
    assert pet.content_rect().getRect()==(31,118,97,110)
    before=pet.content_rect()
    player.advance();assert pet.content_rect()==before
    player.clear();pet.timer.stop();pet.close()


def test_fully_transparent_action_has_safe_fallback(tmp_path,qt_app):
    source=animated_pack(tmp_path/'source')
    Image.new('RGBA',(64,64),(0,255,0,0)).save(source/'idle.webp',lossless=True)
    pack=MaterialLibrary(tmp_path/'library').import_pack(source)
    player=AnimationPlayer();player.load(pack,'idle')
    pet=PetWindow(size=224);pet.player=player
    assert pet.content_rect()==pet.rect()
    player.clear();pet.timer.stop();pet.close()
