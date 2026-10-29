import hashlib,json,time,zipfile
from pathlib import Path
import pytest
from PIL import Image
from workbuddy_pet.builtin import builtin_pack,PACK_ROOT
from workbuddy_pet.materials import ALL_ACTIONS,OPTIONAL_IDLE_ACTIONS,LOOP_ACTIONS,validate_pack,iter_animation,MaterialError

def test_bundled_gifs_preserve_all_authored_frames_and_timing():
    audit=json.loads((Path(__file__).resolve().parents[1]/'art/mint-orbit/user-gifs-v2.0.0.json').read_text())
    pack=validate_pack(PACK_ROOT)
    assert set(pack.actions)==set(ALL_ACTIONS+OPTIONAL_IDLE_ACTIONS)==set(audit)
    assert pack.schema==3 and pack.quality=='hd'
    assert set(PACK_ROOT.parent.iterdir())=={PACK_ROOT,PACK_ROOT.parent/'mint-orbit-idle.png',PACK_ROOT.parent/'blue_fish'}
    for action,spec in pack.actions.items():
        path=PACK_ROOT/spec.file;expected=audit[action]
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected['sha256']
        with Image.open(path) as image:
            durations=[]
            for i in range(image.n_frames):image.seek(i);durations.append(image.info['duration'])
            assert image.size==(720,720) and image.n_frames==16
        assert durations==expected['durations_ms'] and sum(durations)==expected['total_ms']
        assert spec.loop==(action in LOOP_ACTIONS) and spec.loop_range is None
    with Image.open(PACK_ROOT/'actions/idle.gif') as gif,Image.open(PACK_ROOT.parent/'mint-orbit-idle.png') as portrait:
        assert gif.convert('RGBA').tobytes()==portrait.convert('RGBA').tobytes()

def test_export_contains_only_the_new_set_with_unchanged_bytes(tmp_path):
    from workbuddy_pet.templates import export_starter
    with zipfile.ZipFile(export_starter(tmp_path/'pet.zip')) as archive:
        expected={p.relative_to(PACK_ROOT).as_posix() for p in PACK_ROOT.rglob('*') if p.is_file()}
        assert set(archive.namelist())==expected and len(expected)==17
        for name in expected:assert archive.read(name)==(PACK_ROOT/name).read_bytes()

def test_builtin_activates_offline_and_missing_custom_pack_recovers(qt_app,tmp_path):
    from workbuddy_pet.app import Controller
    from workbuddy_pet.settings import Settings,save_settings
    save_settings(tmp_path,Settings(character='f'*32,notifications=False))
    c=Controller(qt_app,tmp_path,True,tmp_path/'absent');c.timer.stop();c.demo_timer.stop()
    assert c.settings.character=='builtin' and c.active_pack.key=='builtin'
    assert c.player.identity[1].endswith('.gif')
    c.enable_card_only();assert c.active_pack is None and c.player.stream is None
    c.activate_character('builtin');assert c.active_pack.key=='builtin' and not c.settings.card_only
    c.shutdown()

@pytest.mark.parametrize('duration,valid',[(300,True),(380,True),(500,True),(501,False),(10,False)])
def test_long_decoder_accepts_authored_holds_but_rejects_excess(tmp_path,duration,valid):
    path=tmp_path/'one.png';Image.new('RGBA',(8,8),'red').save(path,save_all=True,append_images=[Image.new('RGBA',(8,8),'blue')],duration=duration)
    if valid:assert next(iter_animation(path,long=True)).duration==duration
    else:
        with pytest.raises(MaterialError):list(iter_animation(path,long=True))
