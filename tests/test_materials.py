import io
import json
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from workbuddy_pet.materials import MaterialLibrary, MaterialError, decode_animation


def source(root):
    root.mkdir()
    image = Image.new('RGBA',(32,32),(20,90,180,200))
    image.save(root/'idle.png')
    (root/'manifest.json').write_text(json.dumps({'schema':1,'id':'test','name':'测试角色','author':'测试','version':'1.0',
        'license':'CC0-1.0','quality':'light','actions':{'idle':{'file':'idle.png','loop':True}}}),encoding='utf-8')
    return root


def test_folder_zip_fallback_and_remove_only_library(tmp_path):
    original = source(tmp_path/'source')
    library = MaterialLibrary(tmp_path/'library')
    pack = library.import_pack(original)
    assert pack.action('working').file == pack.action('idle').file
    assert library.load(pack.key).name == '测试角色'
    archive = tmp_path/'pet.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for p in original.iterdir(): z.write(p,p.name)
    assert library.import_pack(archive).key == pack.key
    library.remove(pack.key)
    assert not library.list_packs() and (original/'idle.png').exists()
    with pytest.raises(MaterialError):library.remove('../source')


def test_unsafe_zip_and_bad_image_do_not_replace_current(tmp_path):
    library = MaterialLibrary(tmp_path/'library')
    good = library.import_pack(source(tmp_path/'source'))
    for name in ('../escape.png','/escape.png','C:/escape.png','idle.png:stream','CON.png'):
        archive = tmp_path/'bad.zip'
        with zipfile.ZipFile(archive,'w') as z:z.writestr(name,b'bad')
        with pytest.raises(MaterialError): library.import_pack(archive)
    (tmp_path/'source'/'idle.png').write_bytes(b'bad-image')
    with pytest.raises(MaterialError):library.import_pack(tmp_path/'source')
    assert library.load(good.key).name == '测试角色'
    assert not list((tmp_path/'library').glob('stage-*'))


def test_missing_idle_hash_duplicate_and_frame_limit(tmp_path):
    root = source(tmp_path/'source')
    library = MaterialLibrary(tmp_path/'library')
    manifest = json.loads((root/'manifest.json').read_text())
    manifest['files'] = {'idle.png':'0'*64}
    (root/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(MaterialError):library.import_pack(root)
    manifest['files'] = {}
    manifest['actions'] = {}
    (root/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(MaterialError):library.import_pack(root)
    archive=tmp_path/'duplicate.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('A.png',b'one');z.writestr('a.png',b'two')
    with pytest.raises(MaterialError):library.import_pack(archive)
    Image.new('RGBA',(1025,1)).save(root/'large.png')
    with pytest.raises(MaterialError):decode_animation(root/'large.png')


def test_gif_keeps_frame_duration_and_alpha(tmp_path):
    frames = [Image.new('RGBA',(16,16),color) for color in ((0,0,0,0),(90,180,230,255))]
    path=tmp_path/'idle.gif'
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=[80,120],loop=0,disposal=2)
    decoded = decode_animation(path)
    assert len(decoded) == 2 and [f.duration for f in decoded] == [80,120]
