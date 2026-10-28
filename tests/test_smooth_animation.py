from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from workbuddy_pet.materials import CLICK_ACTIONS,alpha_bounds
from workbuddy_pet.ui.animation import AnimationPlayer
from workbuddy_pet.ui.animation_art import pose


def test_click_pose_has_no_vertical_hop():
    for action in CLICK_ACTIONS:
        positions=[pose(action,i/100) for i in range(101)]
        assert all(dx==0 and dy==0 for dx,dy,angle in positions)
        assert max(abs(angle) for dx,dy,angle in positions)<=.8


def test_mid_frame_samples_never_create_unpainted_intermediate_anatomy(qt_app):
    import time
    red=QPixmap(16,16);red.fill(Qt.GlobalColor.red)
    blue=QPixmap(16,16);blue.fill(Qt.GlobalColor.blue)
    player=AnimationPlayer();player.frames=((red,160),(blue,160))
    player.schedule()
    for fraction in (.1,.25,.5,.75,.99):
        player.frame_started=time.monotonic()-.16*fraction
        assert player.pixmap.toImage().pixelColor(8,8).name()=='#ff0000'
    player.advance();assert player.pixmap.toImage().pixelColor(8,8).name()=='#0000ff'
    player.set_visible(False)
    assert not player.timer.isActive()
    player.loop=False;player.index=1;player.advance();assert player.index==1
    player.clear()


def test_generated_seated_typing_keeps_furniture_and_outline_fixed():
    from workbuddy_pet.sprite_sheet import typing_frames
    path=Path(__file__).resolve().parents[1]/'art/mint-orbit/typing-sheet-v1.1.1.png'
    frames=typing_frames(path,256)
    assert len(frames)==8 and all(f.size==(256,256) for f in frames)
    base=frames[0]
    assert all(alpha_bounds(frame)==alpha_bounds(base) for frame in frames)
    assert all(frame.crop((0,180,256,256)).tobytes()==base.crop((0,180,256,256)).tobytes() for frame in frames)
    assert all(frame.crop((190,0,256,256)).tobytes()==base.crop((190,0,256,256)).tobytes() for frame in frames)
    assert any(frame.tobytes()!=base.tobytes() for frame in frames[1:])


def test_seated_leisure_has_fixed_chair_feet_and_distinct_hand_frames():
    from workbuddy_pet.sprite_sheet import leisure_frames
    for action in ('phone','snack'):
        path=Path(__file__).resolve().parents[1]/f'art/mint-orbit/{action}-sheet-v1.2.0.png'
        frames=leisure_frames(path,256);base=frames[0]
        assert len(frames)==8 and all(f.size==(256,256) for f in frames)
        assert all(alpha_bounds(f)==alpha_bounds(base) for f in frames)
        assert all(f.crop((0,193,256,256)).tobytes()==base.crop((0,193,256,256)).tobytes() for f in frames)
        assert len({f.tobytes() for f in frames})==8


def test_action_switch_has_no_previous_pose_overlay(tmp_path,qt_app):
    from types import SimpleNamespace
    from PIL import Image
    for name,color in (('red','red'),('blue','blue')):Image.new('RGBA',(16,16),color).save(tmp_path/f'{name}.png')
    pack=SimpleNamespace(key='synthetic',root=tmp_path,anchor=None,action=lambda state:SimpleNamespace(file=state+'.png',loop=True))
    player=AnimationPlayer();player.load(pack,'red');player.load(pack,'blue')
    assert player.pixmap.toImage().pixelColor(8,8).name()=='#0000ff'
    player.clear()


def test_pet_repaint_clears_pixels_from_the_previous_pose(qt_app):
    from PySide6.QtGui import QPainter,QColor
    from workbuddy_pet.ui.pet import PetWindow
    images=[]
    for left,color in ((10,'red'),(70,'blue')):
        image=QPixmap(100,100);image.fill(Qt.GlobalColor.transparent)
        painter=QPainter(image);painter.fillRect(left,20,20,40,QColor(color));painter.end();images.append(image)
    player=AnimationPlayer();player.frames=tuple((image,10000) for image in images)
    pet=PetWindow();pet.player=player;pet.show();qt_app.processEvents()
    target=pet.image_target_rect(images[0]);x=target.x()+round(target.width()*.2);y=target.y()+round(target.height()*.4)
    assert pet.grab().toImage().pixelColor(x,y).alpha()>200
    player.index=1;pet.update();qt_app.processEvents()
    assert pet.grab().toImage().pixelColor(x,y).alpha()==0
    pet.close();player.clear()
