import io,zipfile
from PIL import Image
from workbuddy_pet.ui.pet import PetWindow


def test_offline_default_portrait_and_vector_fallback(qt_app,tmp_path,monkeypatch):
    import workbuddy_pet.ui.pet as pets
    pet=PetWindow()
    assert not pet.default_pixmap.isNull() and pet.default_pixmap.size().toTuple()==(720,720)
    assert pet.default_pixmap.toImage().pixelColor(0,0).alpha()==0
    pet.timer.stop();pet.close()
    monkeypatch.setattr(pets,'DEFAULT_PORTRAIT',tmp_path/'missing.png')
    fallback=PetWindow()
    assert fallback.default_pixmap.isNull() and not fallback.grab().isNull()
    fallback.timer.stop();fallback.close()


def test_application_icon_is_fixed_original_blue_mascot(qt_app,tmp_path,monkeypatch):
    import workbuddy_pet.ui.pet as pets
    path=tmp_path/'replacement.png';Image.new('RGBA',(64,64),(0,255,0,255)).save(path)
    monkeypatch.setattr(pets,'DEFAULT_PORTRAIT',path)
    image=pets.mascot_icon().pixmap(64,64).toImage()
    assert image.pixelColor(32,10).name()=='#4ba5eb'
    assert image.pixelColor(32,24).name()=='#153754'


def test_material_preview_uses_bundled_animation(qt_app,tmp_path):
    from workbuddy_pet.ui.materials import MaterialPanel
    from workbuddy_pet.materials import MaterialLibrary
    panel=MaterialPanel(MaterialLibrary(tmp_path/'library'))
    assert panel.preview_pack.key=='builtin' and len(panel.preview_pack.actions)==16
    assert panel.action_choice.isEnabled() and not panel.remove.isEnabled()
    assert not hasattr(panel,'light') and not hasattr(panel,'hd')
    panel.shutdown();panel.close()
