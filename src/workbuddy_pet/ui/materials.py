from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,QFileDialog

from ..background import Task
from ..materials import MaterialError, ALL_ACTIONS, OPTIONAL_IDLE_ACTIONS
from ..builtin import builtin_pack,BUILTIN_PACKS
from .animation import AnimationPlayer


class MaterialPanel(QWidget):
    activate_requested=Signal(str)
    remove_requested=Signal(str)
    card_only_requested=Signal()

    def __init__(self,library,parent=None):
        super().__init__(parent)
        self.library,self.job=library,None
        layout=QVBoxLayout(self)
        note=QLabel('支持旧版角色包及15动作完整互动包。导入在本机校验；点击、任务和休闲动作可分别预览。')
        note.setWordWrap(True);layout.addWidget(note)
        self.choices=QComboBox();layout.addWidget(self.choices)
        self.description=QLabel();self.description.setTextFormat(Qt.TextFormat.PlainText);self.description.setWordWrap(True);layout.addWidget(self.description)
        self.preview=QLabel('内置16段动作无需下载');self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter);self.preview.setFixedHeight(130);layout.addWidget(self.preview)
        self.player=AnimationPlayer(self);self.player.changed.connect(self.update_preview)
        self.preview_pack=None
        self.action_choice=QComboBox()
        labels=('待机','思考','玩电脑 / 执行','等待回复','等待确认','完成','失败','点击 · 招手','点击 · 比心',
                '点击 · 害羞','点击 · 惊讶','休闲 · 吃零食','休闲 · 玩手机','休闲 · 伸懒腰','休闲 · 听音乐')
        for action,label in zip(ALL_ACTIONS,labels):self.action_choice.addItem(label,action)
        self.action_choice.addItem('待机挠头（可选）','idle_scratch')
        self.action_choice.currentIndexChanged.connect(self.preview_action)
        layout.addWidget(self.action_choice)
        self.choices.currentIndexChanged.connect(self.preview_selected)
        row=QHBoxLayout()
        self.activate=QPushButton('启用所选角色');self.activate.clicked.connect(lambda:self.activate_requested.emit(self.choices.currentData() or 'builtin'));row.addWidget(self.activate)
        self.remove=QPushButton('删除所选素材');self.remove.clicked.connect(lambda:self.remove_requested.emit(self.choices.currentData()));row.addWidget(self.remove)
        card=QPushButton('仅显示卡片');card.clicked.connect(self.card_only_requested);row.addWidget(card);layout.addLayout(row)
        row=QHBoxLayout()
        self.import_zip=QPushButton('导入 ZIP');self.import_zip.clicked.connect(self.choose_zip);row.addWidget(self.import_zip)
        self.import_folder=QPushButton('导入文件夹');self.import_folder.clicked.connect(self.choose_folder);row.addWidget(self.import_folder)
        self.template=QPushButton('导出当前内置套装');self.template.clicked.connect(self.export_template);row.addWidget(self.template);layout.addLayout(row)
        self.status=QLabel('本地导入不上传文件；分享角色可直接分享素材 ZIP。');self.status.setWordWrap(True);layout.addWidget(self.status)
        layout.addStretch()
        self.reload()

    def reload(self,selected=None):
        selected=selected or self.choices.currentData()
        self.choices.blockSignals(True);self.choices.clear();
        for key in BUILTIN_PACKS:self.choices.addItem(builtin_pack(key).name+' · 内置完整动作',key)
        try:
            for pack in self.library.list_packs():
                self.choices.addItem(pack.name+' · '+('高清' if pack.quality=='hd' else '轻量'),pack.key)
        except MaterialError as error:self.status.setText(str(error))
        self.choices.setCurrentIndex(max(0,self.choices.findData(selected)));self.choices.blockSignals(False)
        self.preview_selected()

    def preview_selected(self):
        key=self.choices.currentData()
        self.preview_pack=None
        self.player.clear()
        self.action_choice.setEnabled(key is not None)
        self.remove.setEnabled(key is not None and key not in BUILTIN_PACKS and self.job is None)
        try:
            if key is None or key in BUILTIN_PACKS:
                from ..builtin import builtin_pack
                pack=builtin_pack(key or 'builtin')
            else:pack=self.library.load(key)
            self.preview_pack=pack
            for action in OPTIONAL_IDLE_ACTIONS:
                index=self.action_choice.findData(action)
                self.action_choice.model().item(index).setEnabled(action in pack.actions)
                if self.action_choice.currentData()==action and action not in pack.actions:self.action_choice.setCurrentIndex(0)
            coverage='完整互动 · 15/15动作' if pack.schema>=2 else f'兼容包 · {len(pack.actions)}/15动作，缺项由内置道具与近似表情补充'
            if 'idle_scratch' in pack.actions:coverage+=' + 待机挠头'
            license_label='用户提供（其他用途需另行授权）' if pack.license=='LicenseRef-User-Provided' else pack.license
            self.description.setText(f'作者：{pack.author}  /  许可：{license_label}\n{coverage}')
            self.preview_action();self.player.set_visible(self.isVisible())
            self.update_preview()
        except MaterialError as error:self.status.setText(str(error));self.preview.setText('素材不可用')

    def preview_action(self):
        if not self.preview_pack:return
        try:
            self.player.load(self.preview_pack,self.action_choice.currentData() or 'idle')
            self.update_preview()
        except MaterialError as error:self.status.setText(str(error))

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

    def start_job(self,function,message,done=None):
        if self.job:return
        self.status.setText(message)
        self.job=Task(function,self)
        self.job.done.connect(done or self.imported)
        self.job.failed.connect(self.status.setText)
        self.job.finished.connect(self.finished)
        for button in (self.import_zip,self.import_folder,self.activate,self.remove,self.template):button.setEnabled(False)
        self.job.start()

    def imported(self,pack):self.reload(pack.key);self.status.setText('素材已导入并可预览，点击“启用所选角色”应用。')

    def finished(self):
        job=self.job;self.job=None
        if job:job.deleteLater()
        for button in (self.import_zip,self.import_folder,self.activate,self.template):button.setEnabled(True)
        self.remove.setEnabled(self.choices.currentData() is not None and self.choices.currentData() not in BUILTIN_PACKS)

    def export_template(self):
        key=self.choices.currentData()
        if key not in BUILTIN_PACKS:key='builtin'
        filename='blue-fish-v1.0.1.zip' if key=='builtin-blue-fish' else 'mint-orbit-user-gifs-v2.0.0.zip'
        path,_=QFileDialog.getSaveFileName(self,'导出内置完整套装',filename,'角色包 (*.zip)')
        if not path:return
        # Copy the original GIFs and their manifest without rendering new artwork.
        if self.job:return
        try:
            from ..templates import export_starter
            export_starter(Path(path),key=key);self.status.setText('完整16段素材已导出，保留原GIF及署名，可直接导入。')
        except (OSError,ValueError):self.status.setText('模板导出失败，请检查保存位置。')

    def shutdown(self):
        self.player.clear()
        if self.job:self.job.cancel.set()
