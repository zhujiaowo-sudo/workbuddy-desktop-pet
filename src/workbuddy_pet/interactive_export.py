"""Render data-only full packs, preserving the source character's attribution."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import zipfile

from PIL import Image
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter

from .materials import ALL_ACTIONS, CLICK_ACTIONS, LOOP_ACTIONS, FALLBACKS, MaterialLibrary, alpha_bounds, decode_animation
from .state import DisplayState
from .ui.animation_art import draw_props, transform_character


def _pil(image):
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    return Image.frombytes('RGBA', (image.width(), image.height()), bytes(image.bits()))


def render_frame(image, action, phase, rect):
    canvas = QImage(image.size(), QImage.Format.Format_RGBA8888)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    transform_character(painter, rect, action, phase)
    painter.drawImage(0, 0, image)
    draw_props(painter, rect, action, phase)
    painter.end()
    return _pil(canvas)


def export_interactive(destination: Path, quality='light', source: Path | None = None, typing_sheet: Path | None = None):
    """Source=None exports only our original CC0 robot, never the built-in portrait."""
    from .ui.pet import PetWindow
    if quality not in ('light', 'hd'):raise ValueError('未知画质')
    if source and typing_sheet is None:raise ValueError('薄荷互动版需要提供坐姿打字精灵图')
    resolution = 256 if quality == 'light' else 512
    payload, boxes = {}, []
    with tempfile.TemporaryDirectory(prefix='wb-pet-export-') as temporary:
        pack = MaterialLibrary(Path(temporary) / 'library').import_pack(source) if source else None
        pet = PetWindow(size=resolution, use_builtin_image=False) if not source else None
        try:
            for action in ALL_ACTIONS:
                if action=='working' and typing_sheet and source:
                    from .sprite_sheet import typing_frames
                    frames=list(typing_frames(typing_sheet,resolution))
                    boxes.extend(alpha_bounds(f) for f in frames)
                    stream=io.BytesIO()
                    frames[0].save(stream,format='WEBP',save_all=True,append_images=frames[1:],duration=160,
                                   loop=0,lossless=True,method=3)
                    payload['actions/working.webp']=stream.getvalue()
                    continue
                base = FALLBACKS.get(action, action)
                # Heart uses a happy source pose; old-pack runtime fallback is more conservative.
                if action == 'click_heart':base = 'done'
                decoded = decode_animation(pack.root / pack.action(base).file) if pack else None
                frames = []
                feet_reference=None
                for index in range(16):
                    phase = index / 16
                    if decoded:
                        frame = decoded[min(len(decoded)-1, round(index*(len(decoded)-1)/15))]
                        image = Image.frombytes('RGBA', frame.size, frame.rgba)
                        image.thumbnail((resolution, resolution), Image.Resampling.LANCZOS)
                        canvas = Image.new('RGBA', (resolution, resolution))
                        canvas.alpha_composite(image, ((resolution-image.width)//2,resolution-image.height))
                    else:
                        pet.display = DisplayState(base, 'connected');pet.tick = index * 6
                        image = _pil(pet.grab().toImage())
                        image.thumbnail((resolution, resolution), Image.Resampling.LANCZOS)
                        canvas = Image.new('RGBA', (resolution,resolution))
                        canvas.alpha_composite(image, ((resolution-image.width)//2,resolution-image.height))
                    bounds = alpha_bounds(canvas)
                    if action in CLICK_ACTIONS:
                        band=round(bounds[1]+(bounds[3]-bounds[1])*.72)
                        feet=canvas.getchannel('A').point(lambda a:255 if a>16 else 0).crop((0,band,resolution,resolution)).getbbox()
                        anchor=((feet[0]+feet[2])/2,band+feet[3])
                        if feet_reference is None:feet_reference=anchor
                        aligned=Image.new('RGBA',canvas.size)
                        aligned.alpha_composite(canvas,(round(feet_reference[0]-anchor[0]),round(feet_reference[1]-anchor[1])))
                        canvas=aligned;bounds=alpha_bounds(canvas)
                    rect = QRectF(bounds[0],bounds[1],bounds[2]-bounds[0],bounds[3]-bounds[1])
                    qimage = QImage(canvas.tobytes(),resolution,resolution,QImage.Format.Format_RGBA8888).copy()
                    rendered = render_frame(qimage,action,phase,rect)
                    boxes.append(alpha_bounds(rendered));frames.append(rendered)
                stream = io.BytesIO()
                frames[0].save(stream,format='WEBP',save_all=True,append_images=frames[1:],duration=160 if action in CLICK_ACTIONS else 80,
                               loop=0,lossless=True,method=3)
                payload[f'actions/{action}.webp'] = stream.getvalue()
        finally:
            if pet:pet.timer.stop();pet.close();pet.deleteLater()
    manifest = {'schema':2, 'id':'mint-orbit-interactive' if source else 'my-interactive-pet',
        'name':'薄荷星伴 · 坐姿互动版' if source else '小搭子 · 完整互动模板',
        'author':pack.author if source else 'WorkBuddy Desktop Pet contributors',
        'version':'1.1.1' if source else '2.0.1','license':pack.license if source else 'CC0-1.0',
        'quality':quality,'anchor':[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)],
        'actions':{a:{'file':f'actions/{a}.webp','loop':a in LOOP_ACTIONS} for a in ALL_ACTIONS},
        'files':{name:hashlib.sha256(data).hexdigest() for name,data in payload.items()}}
    if source:
        manifest['source']={'name':pack.name,'author':pack.author,'version':'1.0.1',
            'license':pack.license,'license_url':'https://creativecommons.org/licenses/by/4.0/',
            'changes':'任务/休闲保留原素材派生；点击去除上下跳动并放慢节奏。working使用imagegen生成的薄荷坐姿打字8关键帧，固定桌椅与外轮廓、注册面部和手部局部动画；显示器朝角色。原1.0.1素材包不变。'}
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        for name,data in payload.items():archive.writestr(name,data)
    return destination
