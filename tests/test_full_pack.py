import json

import pytest
from PIL import Image, ImageDraw

from workbuddy_pet.materials import ALL_ACTIONS, LOOP_ACTIONS, MaterialError, validate_pack


def full_source(root):
    (root/'actions').mkdir(parents=True)
    frames=[]
    for i in range(8):
        image=Image.new('RGBA',(256,256))
        ImageDraw.Draw(image).ellipse((60+i,30,180+i,240),fill='#67bbad')
        frames.append(image)
    for action in ALL_ACTIONS:
        frames[0].save(root/f'actions/{action}.webp',save_all=True,append_images=frames[1:],duration=80,lossless=True)
    manifest={'schema':2,'id':'test','name':'test','author':'test','license':'CC0-1.0','version':'1','quality':'light',
        'anchor':[60,30,188,241],
        'actions':{a:{'file':f'actions/{a}.webp','loop':a in LOOP_ACTIONS} for a in ALL_ACTIONS}}
    (root/'manifest.json').write_text(json.dumps(manifest))
    return manifest


def test_complete_pack_validates_and_exposes_dedicated_actions(tmp_path):
    full_source(tmp_path)
    pack=validate_pack(tmp_path)
    assert pack.schema==2 and len(pack.actions)==15 and pack.anchor==(60,30,188,241)
    assert pack.action('leisure_snack').file=='actions/leisure_snack.webp'


@pytest.mark.parametrize('problem',('missing','extra','alias','loop','static','size','opaque','blank','frames','duration','anchor'))
def test_complete_pack_rejects_incomplete_or_wrong_animation(tmp_path,problem):
    manifest=full_source(tmp_path)
    if problem=='missing':del manifest['actions']['click_wave']
    elif problem=='extra':manifest['actions']['unknown']={'file':'actions/idle.webp'}
    elif problem=='alias':manifest['actions']['click_wave']['file']='actions/idle.webp'
    elif problem=='loop':manifest['actions']['click_wave']['loop']=True
    elif problem=='anchor':manifest['anchor']=[0,0,10,10]
    else:
        size=(128,128) if problem=='size' else (256,256)
        frames=[]
        count=1 if problem=='static' else 17 if problem=='frames' else 8
        for i in range(count):
            image=Image.new('RGBA',size,'blue' if problem=='opaque' else (0,0,0,0))
            if problem!='blank':ImageDraw.Draw(image).rectangle((10+i,20,50+i,80),fill='red')
            frames.append(image)
        frames[0].save(tmp_path/'actions/idle.webp',save_all=True,append_images=frames[1:],
                       duration=20 if problem=='duration' else 80,lossless=True)
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(MaterialError):validate_pack(tmp_path)


def test_exported_template_is_complete_and_uses_original_art(tmp_path,qt_app):
    from workbuddy_pet.interactive_export import export_interactive
    from workbuddy_pet.materials import MaterialLibrary, decode_animation
    result=export_interactive(tmp_path/'template.zip')
    pack=MaterialLibrary(tmp_path/'library').import_pack(result)
    assert pack.schema==2 and len(pack.actions)==15 and pack.license=='CC0-1.0'
    for action in ('working','click_heart','leisure_phone','leisure_snack'):
        frames=decode_animation(pack.root/pack.action(action).file)
        assert len(frames)==16 and frames[0].rgba!=frames[5].rgba


def test_complete_pack_anchor_stays_fixed_across_actions(tmp_path,qt_app):
    from workbuddy_pet.ui.animation import AnimationPlayer
    full_source(tmp_path)
    pack=validate_pack(tmp_path)
    player=AnimationPlayer();player.set_visible(False)
    for action in ALL_ACTIONS:
        player.load(pack,action)
        assert player.content_bounds==pack.anchor
        player.advance();assert player.content_bounds==pack.anchor
    player.clear()
