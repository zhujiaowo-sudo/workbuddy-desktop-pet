from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from workbuddy_pet.materials import CLICK_ACTIONS,alpha_bounds
from workbuddy_pet.ui.animation import AnimationPlayer,blend_pixmaps
from workbuddy_pet.ui.animation_art import pose


def test_click_pose_has_no_vertical_hop():
    for action in CLICK_ACTIONS:
        positions=[pose(action,i/100) for i in range(101)]
        assert all(dx==0 and dy==0 for dx,dy,angle in positions)
        assert max(abs(angle) for dx,dy,angle in positions)<=.8


def test_blending_preserves_alpha_and_target_canvas(qt_app):
    red=QPixmap(16,16);red.fill(Qt.GlobalColor.red)
    blue=QPixmap(16,16);blue.fill(Qt.GlobalColor.blue)
    mixed=blend_pixmaps(red,blue,.5).toImage().pixelColor(8,8)
    assert mixed.red()>100 and mixed.blue()>100 and mixed.alpha()>=254
    large=QPixmap(32,32);large.fill(Qt.GlobalColor.blue)
    assert blend_pixmaps(red,large,0).size()==large.size()


def test_frame_interpolation_and_hidden_clocks(qt_app):
    import time
    red=QPixmap(16,16);red.fill(Qt.GlobalColor.red)
    blue=QPixmap(16,16);blue.fill(Qt.GlobalColor.blue)
    player=AnimationPlayer();player.frames=((red,160),(blue,160))
    player.frame_started=time.monotonic()-.08
    player.schedule()
    mixed=player.pixmap.toImage().pixelColor(8,8)
    assert mixed.red()>70 and mixed.blue()>70
    assert player.smooth_timer.isActive()
    player.set_visible(False)
    assert not player.timer.isActive() and not player.smooth_timer.isActive()
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
