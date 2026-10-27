"""Export the independently drawn mascot as a public, editable character pack."""
import io
import json
import zipfile
from pathlib import Path

from PIL import Image
from PySide6.QtGui import QImage

from .materials import STATES
from .state import DisplayState


def export_starter(destination: Path):
    from .ui.pet import PetWindow
    from PySide6.QtCore import QBuffer, QIODevice
    pet=PetWindow(size=256,use_builtin_image=False)
    try:
        buffer=QBuffer();buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pet.grab().save(buffer,'PNG')
        image=bytes(buffer.data())
    finally:
        pet.timer.stop();pet.close();pet.deleteLater()
    manifest={'schema':1,'id':'my-pet','name':'我的桌宠','author':'请填写作者','version':'1.0.0',
        'license':'请填写素材许可','quality':'light','actions':{'idle':{'file':'idle.png','loop':True}}}
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        archive.writestr('idle.png',image)
    return destination


def export_default(destination: Path, quality='light'):
    from .ui.pet import PetWindow
    if quality not in ('light', 'hd'):
        raise ValueError('未知画质')
    resolution = 256 if quality == 'light' else 512
    pet = PetWindow(size=resolution,use_builtin_image=False)
    payload = {}
    try:
        for state in STATES:
            frames = []
            pet.display = DisplayState(state, 'connected')
            for index in range(12):
                pet.tick = round(index * 2 * 3.141592653589793 * 15 / 12)
                image = pet.grab().toImage().convertToFormat(QImage.Format.Format_RGBA8888)
                frame = Image.frombytes('RGBA', (image.width(), image.height()), bytes(image.bits()))
                frame.thumbnail((resolution,resolution), Image.Resampling.LANCZOS)
                canvas = Image.new('RGBA',(resolution,resolution))
                canvas.alpha_composite(frame,((resolution-frame.width)//2,resolution-frame.height))
                frames.append(canvas)
            buffer = io.BytesIO()
            frames[0].save(buffer,format='WEBP',save_all=True,append_images=frames[1:],
                           duration=100,loop=0,lossless=True,method=2)
            payload[state+'.webp'] = buffer.getvalue()
    finally:
        pet.timer.stop()
        pet.close()
        pet.deleteLater()
    import hashlib
    manifest = {'schema':1, 'id':'xiaodazi', 'name':'小搭子', 'author':'WorkBuddy Desktop Pet contributors',
        'version':'1.0.0', 'license':'CC0-1.0', 'quality':quality,
        'actions':{s:{'file':s+'.webp','loop':s not in ('done','failed')} for s in STATES},
        'files':{name:hashlib.sha256(data).hexdigest() for name,data in payload.items()}}
    destination = Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        for name,data in payload.items():
            archive.writestr(name,data)
    return destination
