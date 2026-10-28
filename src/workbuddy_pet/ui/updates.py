"""Modeless update flow; all network and extraction work stays off the GUI thread."""
import json
from pathlib import Path
import sys
import time

from PySide6.QtCore import QObject,QTimer,Signal,Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QTextEdit,QPushButton,QHBoxLayout,QProgressBar,QCheckBox,QApplication,QLineEdit,QAbstractSpinBox

from .. import __version__
from ..background import Task
from ..update import check_latest,download_release,stage_package,prepare_install,launch_install,UpdateError,RELEASES


class UpdateDialog(QDialog):
    action_requested=Signal()
    cancel_requested=Signal()

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('WorkBuddy 小搭子 · 软件更新');self.resize(420,390)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet('QDialog{background:#fbfeff;} QLabel{color:#36516b;} QPushButton{padding:9px;border-radius:7px;background:#e4f1fb;color:#246b9e;}')
        layout=QVBoxLayout(self)
        self.heading=QLabel();self.heading.setStyleSheet('font-size:16px;font-weight:600;');layout.addWidget(self.heading)
        self.notes=QTextEdit();self.notes.setReadOnly(True);layout.addWidget(self.notes)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        self.progress=QProgressBar();self.progress.setRange(0,100);self.progress.hide();layout.addWidget(self.progress)
        self.restart=QCheckBox('下载后自动安装并重启桌宠');self.restart.setChecked(True);layout.addWidget(self.restart)
        row=QHBoxLayout();self.later=QPushButton('稍后');self.later.clicked.connect(self.close);row.addWidget(self.later)
        self.action=QPushButton('下载更新');self.action.clicked.connect(self.action_requested);row.addWidget(self.action);layout.addLayout(row)

    def closeEvent(self,event):
        self.cancel_requested.emit();event.accept()


class UpdateManager(QObject):
    progress=Signal(int,int,int)

    def __init__(self,controller):
        super().__init__(controller)
        self.controller=controller;self.job=None;self.release=None;self.plan=None;self.phase='idle';self.dismissed=set()
        self.dialog=UpdateDialog(controller.bubble)
        self.dialog.action_requested.connect(self.action)
        self.dialog.cancel_requested.connect(self.cancel)
        self.progress.connect(self.show_progress)
        self.timer=QTimer(self);self.timer.setInterval(6*60*60*1000);self.timer.timeout.connect(self.auto_check)
        if not controller.demo and getattr(sys,'frozen',False):
            self.timer.start();QTimer.singleShot(10000,self.auto_check)
        result=controller.root/'update-result.json'
        if result.is_file():
            try:
                state=json.loads(result.read_text(encoding='utf-8-sig'))['state']
                controller.dialog.update_status.setText({'success':'更新成功，当前版本 '+__version__,'failed':'上次更新失败，已保留或恢复旧版，可重新检查。','restore_failed':'上次更新未完成，请从发布页手动安装；用户数据仍保留。'}.get(state,''))
            except (OSError,ValueError,KeyError):pass

    def auto_check(self):
        if self.controller.settings.auto_update and not self.controller.shutting_down:self.check()

    def check(self,manual=False):
        if self.job or self.controller.shutting_down:
            if manual:self.dialog.show();self.dialog.raise_()
            return
        if (self.phase=='ready' or self.phase=='available' and manual) and self.release:
            if manual or self.release.version not in self.dismissed:self.dialog.show();self.dialog.raise_()
            return
        self.phase='checking';self.dialog.heading.setText('检查新版本');self.dialog.notes.setPlainText('当前版本：'+__version__)
        self.dialog.status.setText('正在连接公开发布服务器…');self.dialog.action.setEnabled(False);self.dialog.progress.hide()
        if manual:self.dialog.show();self.dialog.raise_()
        self.job=Task(lambda:check_latest(__version__),self)
        def done(release):
            self.release=release
            if release:
                self.phase='available';self.dialog.heading.setText('发现新版本 '+release.version)
                self.dialog.notes.setPlainText(release.notes)
                self.dialog.status.setText(f'当前 {__version__} → {release.version} · {release.size/1024/1024:.1f} MB\n下载期间可继续使用；安装只重启桌宠，WorkBuddy 任务继续运行。')
                self.dialog.action.setText('下载并更新');self.dialog.action.setEnabled(True)
                if manual or release.version not in self.dismissed:self.dialog.show();self.dialog.raise_()
            else:
                self.phase='idle';self.dialog.heading.setText('已是最新版本 '+__version__)
                self.dialog.status.setText('未发现更高的正式版本。');self.dialog.action.setText('再次检查');self.dialog.action.setEnabled(True)
            self.controller.dialog.update_status.setText(self.dialog.heading.text())
        self.job.done.connect(done);self.job.failed.connect(lambda message:self.failed(message,manual))
        self.job.finished.connect(self.finished);self.job.start()

    def action(self):
        if self.job:return
        if self.phase=='ready':
            try:
                process=launch_install(self.plan)
                if process.poll() is not None:raise UpdateError('更新安装助手未启动，请重试')
                self.phase='installing';self.dialog.action.setEnabled(False)
                self.dialog.status.setText('安装助手正在核对暂存文件，验证成功后重启…')
                self.wait_helper(process,time.monotonic()+20)
            except (OSError,UpdateError) as error:self.failed(str(error),True)
        elif self.release:self.download()
        else:self.check(manual=True)

    def wait_helper(self,process,deadline):
        # Keep this app running if helper validation fails, rather than quitting first.
        if self.controller.shutting_down:return
        if process.poll() is not None:
            self.failed('安装准备失败，当前程序继续运行，可重试。',True);return
        if self.plan.with_name('helper-ready').is_file():self.controller.app.quit();return
        if time.monotonic()>=deadline:
            process.terminate();self.failed('安装助手响应超时，当前程序继续运行。',True);return
        QTimer.singleShot(100,lambda:self.wait_helper(process,deadline))

    def download(self):
        if not getattr(sys,'frozen',False):
            self.dialog.status.setText('源码运行请更新 Git 仓库。Windows 发布版支持一键安装。');return
        self.phase='downloading';self.dialog.action.setEnabled(False);self.dialog.later.setText('取消下载')
        self.dialog.progress.show();self.dialog.progress.setValue(0);self.dialog.status.setText('正在下载…')
        install=Path(sys.executable).parent
        def run():
            cancel=self.job.cancel.is_set
            archive=download_release(self.release,self.controller.root/'updates',cancel,self.progress.emit)
            stage=stage_package(archive,install,cancel)
            if cancel():raise UpdateError('已取消更新')
            return prepare_install(stage,install,self.controller.root,version=self.release.version)
        self.job=Task(run,self)
        def done(plan):
            self.plan=plan;self.phase='ready';self.dialog.action.setEnabled(True);self.dialog.action.setText('重启并安装')
            self.dialog.later.setText('稍后');self.dialog.status.setText('下载、校验及准备完成。点击重启安装，设置和素材会保留。')
            if self.dialog.restart.isChecked():QTimer.singleShot(100,self.auto_install)
        self.job.done.connect(done);self.job.failed.connect(lambda message:self.failed(message,True))
        self.job.finished.connect(self.finished);self.job.start()

    def auto_install(self):
        if self.phase!='ready' or self.controller.shutting_down or not self.dialog.restart.isChecked():return
        focus=QApplication.focusWidget()
        editing=isinstance(focus,(QLineEdit,QAbstractSpinBox)) and self.controller.bubble.isAncestorOf(focus)
        busy=self.controller.bubble.materials.job or self.controller.pet.press_position is not None
        if self.job or busy or editing:
            self.dialog.status.setText('更新已就绪，等待当前编辑或素材操作结束后自动安装；也可点击重启安装。')
            QTimer.singleShot(1000,self.auto_install);return
        self.action()

    def show_progress(self,done,total,attempt):
        self.dialog.progress.setValue(int(done*100/total))
        self.dialog.status.setText(f'下载 {done/1024/1024:.1f} / {total/1024/1024:.1f} MB · 第 {attempt}/3 次尝试' if done<total else '下载完成，正在校验并准备安装…')

    def failed(self,message,show):
        if self.phase=='checking':self.release=None
        self.phase='error';self.dialog.status.setText(message);self.dialog.action.setText('重试');self.dialog.action.setEnabled(True);self.dialog.later.setText('稍后')
        self.controller.dialog.update_status.setText('更新失败，可手动重试。')
        if show:self.dialog.show()

    def finished(self):
        job=self.job;self.job=None
        if job:job.deleteLater()
        if self.phase=='error':
            self.dialog.action.setEnabled(True);self.dialog.action.setText('重试');self.dialog.later.setText('稍后')
            if job and job.cancel.is_set():self.dialog.status.setText('已取消下载，可稍后重试。')

    def cancel(self):
        if self.release:self.dismissed.add(self.release.version)
        if self.job and self.phase=='downloading':self.job.cancel.set();self.phase='error'

    def shutdown(self):
        self.timer.stop()
        if self.job:self.job.cancel.set()
        self.dialog.hide()
