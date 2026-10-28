"""Display authored frames faithfully; never cross-dissolve different anatomy."""
import time
from PySide6.QtCore import QObject,QTimer,Signal
from PySide6.QtGui import QImage,QPixmap
from ..materials import decode_animation


class AnimationPlayer(QObject):
    changed=Signal()
    bounds_changed=Signal()

    def __init__(self,parent=None):
        super().__init__(parent)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.advance)
        self.frames=();self.index=0;self.loop=True;self.visible=True
        self.identity=None;self.content_bounds=None;self.frame_started=0

    @property
    def pixmap(self):
        return self.frames[self.index][0] if self.frames else None

    def load(self,pack,state):
        action=pack.action(state);identity=(pack.key,action.file,action.loop)
        if identity==self.identity:return
        frames=decode_animation(pack.root/action.file);prepared=[]
        for frame in frames:
            image=QImage(frame.rgba,*frame.size,QImage.Format.Format_RGBA8888).copy()
            prepared.append((QPixmap.fromImage(image),frame.duration))
        self.clear(notify=False)
        self.frames,self.identity,self.loop=tuple(prepared),identity,action.loop
        self.frame_started=time.monotonic()
        boxes=[frame.bounds for frame in frames if frame.bounds is not None]
        self.content_bounds=pack.anchor or ((min(b[0] for b in boxes),min(b[1] for b in boxes),
            max(b[2] for b in boxes),max(b[3] for b in boxes)) if boxes else None)
        self.bounds_changed.emit();self.changed.emit();self.schedule()

    def clear(self,*,notify=True):
        had_frames=bool(self.frames);self.timer.stop()
        self.frames=();self.index=0;self.identity=None;self.content_bounds=None
        if notify and had_frames:self.bounds_changed.emit();self.changed.emit()

    def set_visible(self,value):
        self.visible=value
        if value:self.frame_started=time.monotonic();self.schedule()
        else:self.timer.stop()

    def schedule(self):
        if self.visible and len(self.frames)>1 and (self.loop or self.index<len(self.frames)-1):
            self.timer.start(self.frames[self.index][1])

    def advance(self):
        if not self.frames:return
        if not self.loop and self.index==len(self.frames)-1:self.timer.stop();return
        self.index=(self.index+1)%len(self.frames);self.frame_started=time.monotonic()
        self.changed.emit();self.schedule()
