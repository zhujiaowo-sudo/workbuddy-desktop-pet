import io,zipfile
from PIL import Image
from workbuddy_pet.ui.pet import PetWindow


def test_offline_default_portrait_and_vector_fallback(qt_app,tmp_path,monkeypatch):
    import workbuddy_pet.ui.pet as pets
    pet=PetWindow()
    assert not pet.default_pixmap.isNull() and pet.default_pixmap.size().toTuple()==(512,512)
    assert pet.default_pixmap.toImage().pixelColor(0,0).alpha()==0
    pet.timer.stop();pet.close()
    monkeypatch.setattr(pets,'DEFAULT_PORTRAIT',tmp_path/'missing.png')
    fallback=PetWindow()
    assert fallback.default_pixmap.isNull() and not fallback.grab().isNull()
    fallback.timer.stop();fallback.close()


def test_template_does_not_redistribute_default_portrait_as_original(qt_app,tmp_path,monkeypatch):
    import workbuddy_pet.ui.pet as pets
    from workbuddy_pet.templates import export_starter
    path=tmp_path/'synthetic.png';Image.new('RGBA',(32,32),(0,255,0,255)).save(path)
    monkeypatch.setattr(pets,'DEFAULT_PORTRAIT',path)
    result=export_starter(tmp_path/'template.zip')
    with zipfile.ZipFile(result) as archive:
        image=Image.open(io.BytesIO(archive.read('idle.png'))).convert('RGBA')
        assert image.getpixel((image.width//2,image.height//2))!=(0,255,0,255)
