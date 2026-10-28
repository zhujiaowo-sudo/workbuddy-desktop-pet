"""Decode once per action; interpolate gently and stop all clocks while hidden."""
import time

from PySide6.QtCore import QObject, QTimer, Signal, QVariantAnimation, QEasingCurve, Qt, QRect
from PySide6.QtGui import QImage, QPixmap, QPainter

from ..materials import decode_animation


def blend_pixmaps(previous, current, amount):
    if amount<=0 and previous.size()==current.size():return previous
    if amount>=1:return current
    canvas=QPixmap(current.size());canvas.fill(Qt.GlobalColor.transparent)
    painter=QPainter(canvas);painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    target=previous.size().scaled(current.size(),Qt.AspectRatioMode.KeepAspectRatio)
    rect=QRect((current.width()-target.width())//2,current.height()-target.height(),target.width(),target.height())
    painter.setOpacity(1-amount);painter.drawPixmap(rect,previous,previous.rect())
    # Weighted premultiplied pixels: shared opaque regions stay opaque throughout.
    # Apply opacity BEFORE Plus. Qt otherwise applies coverage after saturating
    # source alpha and makes a shared opaque region 75% opaque at the midpoint.
    weighted=QPixmap(current.size());weighted.fill(Qt.GlobalColor.transparent)
    weight_painter=QPainter(weighted);weight_painter.setOpacity(amount)
    weight_painter.drawPixmap(0,0,current);weight_painter.end()
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
    painter.setOpacity(1);painter.drawPixmap(0,0,weighted);painter.end()
    return canvas


class AnimationPlayer(QObject):
    changed = Signal()
    bounds_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.advance)
        self.smooth_timer=QTimer(self);self.smooth_timer.setInterval(33);self.smooth_timer.timeout.connect(self.invalidate)
        self.frames=();self.index=0;self.loop=True;self.visible=True
        self.identity=None;self.content_bounds=None;self.frame_started=0
        self.previous_pixmap=None;self.fade=1.0;self._render_cache=None
        self.transition=QVariantAnimation(self);self.transition.setDuration(180)
        self.transition.setStartValue(0.0);self.transition.setEndValue(1.0)
        self.transition.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.transition.valueChanged.connect(self._fade_changed)
        self.transition.finished.connect(self._fade_finished)

    def invalidate(self):self._render_cache=None;self.changed.emit()

    def _fade_changed(self,value):self.fade=float(value);self.invalidate()

    def _fade_finished(self):self.fade=1.0;self.previous_pixmap=None;self.invalidate()

    @property
    def pixmap(self):
        if not self.frames:return None
        if self._render_cache is not None:return self._render_cache
        current,duration=self.frames[self.index]
        if self.visible and len(self.frames)>1 and (self.loop or self.index<len(self.frames)-1):
            amount=min(1,max(0,(time.monotonic()-self.frame_started)*1000/duration))
            current=blend_pixmaps(current,self.frames[(self.index+1)%len(self.frames)][0],amount)
        if self.previous_pixmap is not None and self.fade<1:
            current=blend_pixmaps(self.previous_pixmap,current,self.fade)
        self._render_cache=current
        return current

    def load(self, pack, state):
        action=pack.action(state);identity=(pack.key,action.file,action.loop)
        if identity==self.identity:return
        frames=decode_animation(pack.root/action.file);prepared=[]
        for frame in frames:
            image=QImage(frame.rgba,*frame.size,QImage.Format.Format_RGBA8888).copy()
            prepared.append((QPixmap.fromImage(image),frame.duration))
        previous=self.pixmap
        self.clear(notify=False)
        self.frames,self.identity,self.loop=tuple(prepared),identity,action.loop
        self.frame_started=time.monotonic()
        boxes=[f.bounds for f in frames if f.bounds is not None]
        self.content_bounds=pack.anchor or ((min(b[0] for b in boxes),min(b[1] for b in boxes),
                                           max(b[2] for b in boxes),max(b[3] for b in boxes)) if boxes else None)
        if self.visible and previous is not None:
            self.previous_pixmap=previous;self.fade=0.0;self.transition.start()
        self.bounds_changed.emit();self.invalidate();self.schedule()

    def clear(self,*,notify=True):
        had_frames=bool(self.frames)
        self.timer.stop();self.smooth_timer.stop();self.transition.stop()
        self.frames,self.identity,self.index=(),None,0
        self.content_bounds=None;self.previous_pixmap=None;self.fade=1.0;self._render_cache=None
        if notify and had_frames:self.bounds_changed.emit();self.changed.emit()

    def set_visible(self,value):
        if value and not self.visible:self.frame_started=time.monotonic()
        self.visible=value;self._render_cache=None
        if value:self.schedule()
        else:
            self.timer.stop();self.smooth_timer.stop();self.transition.stop()
            self.previous_pixmap=None;self.fade=1.0

    def schedule(self):
        if self.visible and len(self.frames)>1 and (self.loop or self.index<len(self.frames)-1):
            self.timer.start(self.frames[self.index][1]);self.smooth_timer.start()
        else:self.smooth_timer.stop()

    def advance(self):
        if self.frames:
            if not self.loop and self.index==len(self.frames)-1:
                self.timer.stop();self.smooth_timer.stop();return
            self.index=(self.index+1)%len(self.frames);self.frame_started=time.monotonic()
            self.invalidate();self.schedule()
