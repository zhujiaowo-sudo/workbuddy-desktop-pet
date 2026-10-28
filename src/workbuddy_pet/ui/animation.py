"""Display authored frames faithfully; never cross-dissolve different anatomy."""
import time
import math
import queue
from PySide6.QtCore import QObject,QTimer,Signal,Qt
from PySide6.QtGui import QImage,QPixmap
from ..materials import decode_animation,MaterialError
from .frame_stream import FrameStream


class AnimationPlayer(QObject):
    changed=Signal()
    bounds_changed=Signal()
    finished=Signal()

    def __init__(self,parent=None):
        super().__init__(parent)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self._timeout);self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.frames=();self.index=0;self.loop=True;self.visible=True
        self.identity=None;self.content_bounds=None;self.canvas_size=None;self.frame_started=0
        self.stream=None;self.stream_path=None;self.deadline=0;self.error=None;self.pending=None;self.loop_range=None;self.ended=False

    @property
    def pixmap(self):
        return self.frames[self.index][0] if self.frames else None

    def load(self,pack,state,*,defer=False):
        action=pack.action(state);identity=(pack.key,action.file,action.loop,getattr(action,'loop_range',None))
        if identity==self.identity:
            if self.error:raise MaterialError(self.error)
            if self.stream and self.stream.tail_started.is_set() and not self.ended:
                self.pending=(pack,state)
            else:
                self.pending=None
                if self.stream and not self.stream.done.is_set():self.stream.exit.clear()
            return
        if defer and self.stream and not self.ended:
            self.pending=(pack,state);self.stream.exit.set();return
        if getattr(pack, 'schema', 1) == 3:
            self.clear(notify=False)
            self.identity=identity;self.loop=action.loop;self.content_bounds=pack.anchor
            self.canvas_size=(720,720) if pack.quality=='hd' else (512,512)
            self.stream_path=pack.root/action.file;self.loop_range=getattr(action,'loop_range',None)
            if self.visible:self.stream=FrameStream(self.stream_path,self.loop,self.loop_range);self.timer.start(1)
            self.bounds_changed.emit();self.changed.emit()
            return
        frames=decode_animation(pack.root/action.file);prepared=[]
        for frame in frames:
            image=QImage(frame.rgba,*frame.size,QImage.Format.Format_RGBA8888).copy()
            prepared.append((QPixmap.fromImage(image),frame.duration))
        self.clear(notify=False)
        self.frames,self.identity,self.loop=tuple(prepared),identity,action.loop
        self.frame_started=time.perf_counter()
        boxes=[frame.bounds for frame in frames if frame.bounds is not None]
        self.content_bounds=pack.anchor or ((min(b[0] for b in boxes),min(b[1] for b in boxes),
            max(b[2] for b in boxes),max(b[3] for b in boxes)) if boxes else None)
        self.deadline=time.perf_counter()+self.frames[0][1]/1000
        self.bounds_changed.emit();self.changed.emit();self.schedule()

    def clear(self,*,notify=True):
        had_frames=bool(self.frames or self.stream_path);self.timer.stop()
        if self.stream:self.stream.close()
        self.stream=None;self.stream_path=None;self.deadline=0;self.error=None;self.pending=None;self.loop_range=None;self.ended=False
        self.frames=();self.index=0;self.identity=None;self.content_bounds=None;self.canvas_size=None
        if notify and had_frames:self.bounds_changed.emit();self.changed.emit()

    def set_visible(self,value):
        if self.visible == value:return
        self.visible=value
        if self.stream_path:
            self.pending=None;self.ended=False
            if self.stream:self.stream.close()
            self.stream=None;self.deadline=0
            if value:self.stream=FrameStream(self.stream_path,self.loop,self.loop_range);self.timer.start(1)
        elif value:
            self.frame_started=time.perf_counter()
            self.deadline=self.frame_started+(self.frames[self.index][1]/1000 if self.frames else 0)
            self.schedule()
        else:self.timer.stop()
        if not value:self.timer.stop()

    def schedule(self):
        if self.visible and len(self.frames)>1 and (self.loop or self.index<len(self.frames)-1):
            delay=max(1,math.ceil((self.deadline-time.perf_counter())*1000)) if self.deadline else self.frames[self.index][1]
            self.timer.start(delay)
        else:self.timer.stop()

    def _timeout(self):
        if self.stream:
            self._stream_tick();return
        if not self.frames or not self.visible:return
        now=time.perf_counter()
        # Deadline advances from the source timeline, never from a late GUI callback.
        if self.loop:
            cycle=sum(frame[1] for frame in self.frames)/1000
            if now-self.deadline>=cycle:self.deadline+=int((now-self.deadline)//cycle)*cycle
        changed=False
        while now>=self.deadline:
            if not self.loop and self.index==len(self.frames)-1:break
            self.index=(self.index+1)%len(self.frames)
            self.deadline+=self.frames[self.index][1]/1000
            changed=True
        if changed:self.changed.emit()
        self.schedule()

    def _stream_tick(self):
        if not self.visible or not self.stream:return
        now=time.perf_counter();latest=None
        while not self.deadline or now>=self.deadline:
            try:frame=self.stream.frames.get_nowait()
            except queue.Empty:break
            latest=frame
            self.deadline=(self.deadline or now)+frame.duration/1000
        if latest:
            image=QImage(latest.rgba,*latest.size,QImage.Format.Format_RGBA8888).copy()
            self.frames=((QPixmap.fromImage(image),latest.duration),);self.index=0
            self.changed.emit()
        if self.stream.done.is_set() and self.stream.frames.empty():
            self.error=self.stream.error
            if self.error:return
            if self.deadline>now:
                self.timer.start(max(1,math.ceil((self.deadline-now)*1000)));return
            self.ended=True
            if self.pending:
                pack,state=self.pending
                self.clear(notify=False);self.load(pack,state)
            else:self.finished.emit()
            return
        self.timer.start(max(1,math.ceil((self.deadline-now)*1000)) if self.deadline>now else 5)

    def advance(self):
        """Explicit next-frame operation for previews; timer uses the source clock."""
        if not self.frames:return
        if not self.loop and self.index==len(self.frames)-1:self.timer.stop();return
        self.index=(self.index+1)%len(self.frames);self.frame_started=time.perf_counter()
        self.deadline=self.frame_started+self.frames[self.index][1]/1000
        self.changed.emit();self.schedule()
