from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,QFileDialog

from ..background import Task
from ..materials import MaterialError
from .animation import AnimationPlayer


class MaterialPanel(QWidget):
    activate_requested=Signal(str)
    remove_requested=Signal(str)
    card_only_requested=Signal()

    def __init__(self,library,parent=None):
        super().__init__(parent)
        self.library,self.job=library,None
        layout=QVBoxLayout(self)
        note=QLabel('素材包保存在本机角色库。至少需要待机动作；其他动作缺失时回退待机。')
        note.setWordWrap(True);layout.addWidget(note)
        self.choices=QComboBox();layout.addWidget(self.choices)
        self.description=QLabel();self.description.setTextFormat(Qt.TextFormat.PlainText);self.description.setWordWrap(True);layout.addWidget(self.description)
        self.preview=QLabel('薄荷星伴静态形象无需下载');self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter);self.preview.setFixedHeight(130);layout.addWidget(self.preview)
        self.player=AnimationPlayer(self);self.player.changed.connect(self.update_preview)
        self.choices.currentIndexChanged.connect(self.preview_selected)
        row=QHBoxLayout()
        self.activate=QPushButton('启用所选角色');self.activate.clicked.connect(lambda:self.activate_requested.emit(self.choices.currentData() or 'builtin'));row.addWidget(self.activate)
        self.remove=QPushButton('删除所选素材');self.remove.clicked.connect(lambda:self.remove_requested.emit(self.choices.currentData()));row.addWidget(self.remove)
        card=QPushButton('仅显示卡片');card.clicked.connect(self.card_only_requested);row.addWidget(card);layout.addLayout(row)
        row=QHBoxLayout()
        self.import_zip=QPushButton('导入 ZIP');self.import_zip.clicked.connect(self.choose_zip);row.addWidget(self.import_zip)
        self.import_folder=QPushButton('导入文件夹');self.import_folder.clicked.connect(self.choose_folder);row.addWidget(self.import_folder)
        template=QPushButton('导出创作模板');template.clicked.connect(self.export_template);row.addWidget(template);layout.addLayout(row)
        row=QHBoxLayout()
        self.light=QPushButton('下载默认轻量包 · 256px');self.light.clicked.connect(lambda:self.download('light'));row.addWidget(self.light)
        self.hd=QPushButton('下载默认高清包 · 512px');self.hd.clicked.connect(lambda:self.download('hd'));row.addWidget(self.hd);layout.addLayout(row)
        self.status=QLabel('本地导入不上传文件；分享角色可直接分享素材 ZIP。');self.status.setWordWrap(True);layout.addWidget(self.status)
        layout.addStretch()
        self.reload()

    def reload(self,selected=None):
        selected=selected or self.choices.currentData()
        self.choices.blockSignals(True);self.choices.clear();self.choices.addItem('薄荷星伴 · 内置静态形象','builtin')
        try:
            for pack in self.library.list_packs():
                self.choices.addItem(pack.name+' · '+('高清' if pack.quality=='hd' else '轻量'),pack.key)
        except MaterialError as error:self.status.setText(str(error))
        self.choices.setCurrentIndex(max(0,self.choices.findData(selected)));self.choices.blockSignals(False)
        self.preview_selected()

    def preview_selected(self):
        key=self.choices.currentData()
        self.player.clear()
        self.remove.setEnabled(key not in (None,'builtin') and self.job is None)
        if key in (None,'builtin'):
            from .pet import DEFAULT_PORTRAIT,mascot_icon
            portrait=QPixmap(str(DEFAULT_PORTRAIT))
            self.preview.setPixmap(portrait.scaled(125,125,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
                                   if not portrait.isNull() else mascot_icon().pixmap(110,110))
            self.description.setText('作者：Buddy娘 / CC-BY-4.0\n默认静态形象随程序提供，7状态动画可独立下载。')
            return
        try:
            pack=self.library.load(key)
            self.description.setText(f'作者：{pack.author}  /  许可：{pack.license}')
            self.player.load(pack,'idle');self.player.set_visible(self.isVisible())
            self.update_preview()
        except MaterialError as error:self.status.setText(str(error));self.preview.setText('素材不可用')

    def update_preview(self):
        if self.player.pixmap:
            self.preview.setPixmap(self.player.pixmap.scaled(125,125,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))

    def showEvent(self,event):super().showEvent(event);self.player.set_visible(True)
    def hideEvent(self,event):super().hideEvent(event);self.player.set_visible(False)

    def choose_zip(self):
        path,_=QFileDialog.getOpenFileName(self,'导入角色 ZIP','','角色包 (*.zip)')
        if path:self.import_path(Path(path))

    def choose_folder(self):
        path=QFileDialog.getExistingDirectory(self,'选择直接包含 manifest.json 的角色目录')
        if path:self.import_path(Path(path))

    def import_path(self,path):self.start_job(lambda:self.library.import_pack(path),'正在检查并导入素材…')

    def download(self,quality):
        from ..material_download import download_default
        self.start_job(lambda:download_default(quality,self.library,lambda:self.job is None or self.job.cancel.is_set()),'正在下载并校验默认素材…')

    def start_job(self,function,message):
        if self.job:return
        self.status.setText(message)
        self.job=Task(function,self)
        self.job.done.connect(self.imported)
        self.job.failed.connect(self.status.setText)
        self.job.finished.connect(self.finished)
        for button in (self.import_zip,self.import_folder,self.light,self.hd,self.activate,self.remove):button.setEnabled(False)
        self.job.start()

    def imported(self,pack):self.reload(pack.key);self.status.setText('素材已导入并可预览，点击“启用所选角色”应用。')

    def finished(self):
        job=self.job;self.job=None
        if job:job.deleteLater()
        for button in (self.import_zip,self.import_folder,self.light,self.hd,self.activate):button.setEnabled(True)
        self.remove.setEnabled(self.choices.currentData() not in (None,'builtin'))

    def export_template(self):
        path,_=QFileDialog.getSaveFileName(self,'导出可直接导入的创作模板','my-pet-template.zip','角色包 (*.zip)')
        if not path:return
        try:
            from ..templates import export_starter
            export_starter(Path(path));self.status.setText('模板已导出：替换 idle.png、修改清单后即可导入。')
        except (OSError,ValueError):self.status.setText('模板导出失败，请检查保存位置。')

    def shutdown(self):
        self.player.clear()
        if self.job:self.job.cancel.set()
