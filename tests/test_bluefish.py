import json,hashlib,zipfile
from pathlib import Path
from workbuddy_pet.builtin import builtin_pack,BUILTIN_PACKS
from workbuddy_pet.materials import validate_pack
from workbuddy_pet.settings import Settings,save_settings,load_settings
def test_new_set_matches_source_and_keeps_original():
    assert builtin_pack().name=='薄荷星伴'
    p=builtin_pack('builtin-blue-fish');assert p.name=='蓝色小鱼' and len(validate_pack(p.root).actions)==16
    audit=json.loads((Path(__file__).resolve().parents[1]/'art/blue-fish/user-gifs-v1.0.0.json').read_text())
    for a,spec in p.actions.items():assert hashlib.sha256((p.root/spec.file).read_bytes()).hexdigest()==audit[a]['sha256']
def test_selection_persists_and_controller_switches(qt_app,tmp_path):
    from workbuddy_pet.app import Controller
    save_settings(tmp_path,Settings(character='builtin-blue-fish',notifications=False))
    assert load_settings(tmp_path).character=='builtin-blue-fish'
    c=Controller(qt_app,tmp_path,True,tmp_path/'absent');c.timer.stop();c.demo_timer.stop()
    try:
        assert c.active_pack.name=='蓝色小鱼'
        assert c.bubble.materials.choices.findData('builtin')>=0 and c.bubble.materials.choices.findData('builtin-blue-fish')>=0
        c.remove_character('builtin-blue-fish');assert c.active_pack.name=='蓝色小鱼'
        c.activate_character('builtin');assert c.active_pack.name=='薄荷星伴'
        c.activate_character('builtin-blue-fish');assert c.active_pack.name=='蓝色小鱼'
    finally:c.shutdown()
def test_export_selected_set(tmp_path):
    from workbuddy_pet.templates import export_starter
    with zipfile.ZipFile(export_starter(tmp_path/'fish.zip',key='builtin-blue-fish')) as z:
        assert len(z.namelist())==17 and json.loads(z.read('manifest.json'))['id']=='blue-fish'
