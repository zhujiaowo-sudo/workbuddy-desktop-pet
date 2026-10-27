from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLineEdit, QTextEdit, QLabel, QPushButton, QApplication

from ..background import Task
from ..chat import ChatClient, ChatConfig, load_chat_config, save_chat_config


class ChatPanel(QWidget):
    open_requested=Signal()

    def __init__(self,root,workbuddy_path,home,parent=None):
        super().__init__(parent)
        self.root,self.executable,self.home=root,workbuddy_path,home
        self.client=ChatClient()
        self.job=None
        self.messages=[]
        config=load_chat_config(root)
        layout=QVBoxLayout(self)
        note=QLabel('独立闲聊 · 不会接管 WorkBuddy 现有任务或执行工具。对话仅在本次运行中保留。')
        note.setWordWrap(True);layout.addWidget(note)
        self.backend=QComboBox()
        self.backend.addItem('WorkBuddy 本机 CLI（需该通道可用）','workbuddy-cli')
        self.backend.addItem('兼容 Chat Completions 的模型接口','api')
        self.backend.setCurrentIndex(max(0,self.backend.findData(config.backend)))
        layout.addWidget(self.backend)
        self.connection=QWidget();form=QFormLayout(self.connection);form.setContentsMargins(0,0,0,0)
        self.endpoint=QLineEdit(config.endpoint);self.endpoint.setPlaceholderText('https://服务地址/v1 或 http://127.0.0.1:端口/v1')
        self.model=QLineEdit(config.model);self.model.setPlaceholderText('模型 ID')
        self.key=QLineEdit(config.key);self.key.setEchoMode(QLineEdit.EchoMode.Password);self.key.setPlaceholderText('密钥由 Windows 用户加密后保存；本机服务可留空')
        form.addRow('地址',self.endpoint);form.addRow('模型',self.model);form.addRow('密钥',self.key)
        layout.addWidget(self.connection)
        self.save=QPushButton('保存聊天连接');self.save.clicked.connect(self.save_config);layout.addWidget(self.save)
        self.backend.currentIndexChanged.connect(self.show_connection);self.show_connection()
        self.transcript=QTextEdit();self.transcript.setReadOnly(True);self.transcript.setMinimumHeight(110);layout.addWidget(self.transcript,1)
        self.draft=QTextEdit();self.draft.setPlaceholderText('输入消息，点击发送');self.draft.setMaximumHeight(70);layout.addWidget(self.draft)
        buttons=QHBoxLayout()
        self.send=QPushButton('发送');self.send.clicked.connect(self.submit);buttons.addWidget(self.send)
        self.cancel_button=QPushButton('取消');self.cancel_button.clicked.connect(self.cancel);self.cancel_button.setEnabled(False);buttons.addWidget(self.cancel_button)
        copy=QPushButton('复制草稿');copy.clicked.connect(lambda:QApplication.clipboard().setText(self.draft.toPlainText()));buttons.addWidget(copy)
        open_button=QPushButton('打开 WorkBuddy');open_button.clicked.connect(self.open_requested);buttons.addWidget(open_button)
        layout.addLayout(buttons)
        self.status=QLabel('发送内容将交给所选模型服务处理。');self.status.setWordWrap(True);layout.addWidget(self.status)

    def show_connection(self):self.connection.setVisible(self.backend.currentData()=='api')

    def config(self):return ChatConfig(self.backend.currentData(),self.endpoint.text().strip(),self.model.text().strip(),self.key.text())

    def save_config(self):
        try:save_chat_config(self.root,self.config());self.status.setText('聊天连接已保存，密钥不会进入诊断或角色包。')
        except (OSError,ValueError) as error:self.status.setText(str(error))

    def submit(self):
        text=self.draft.toPlainText().strip()
        if self.job or not text:return
        if len(text)>8000:self.status.setText('消息最多 8000 字符。');return
        messages=[*self.messages,{'role':'user','content':text}]
        config=self.config()
        self.send.setEnabled(False);self.cancel_button.setEnabled(True);self.status.setText('正在等待文本回复…')
        self.job=Task(lambda:self.client.complete(config,messages,workbuddy_path=self.executable(),home=self.home,cwd=str(self.root)),self)
        self.job.done.connect(lambda reply:self.received(text,reply))
        self.job.failed.connect(self.status.setText)
        self.job.finished.connect(self.finished)
        self.job.start()

    def received(self,text,reply):
        self.messages=[*self.messages,{'role':'user','content':text},{'role':'assistant','content':reply}][-12:]
        self.transcript.setPlainText('\n\n'.join(('你：' if m['role']=='user' else '小搭子：')+m['content'] for m in self.messages))
        if self.draft.toPlainText().strip()==text:self.draft.clear()
        self.status.setText('回复完成。')

    def finished(self):
        job=self.job;self.job=None
        if job:job.deleteLater()
        self.send.setEnabled(True);self.cancel_button.setEnabled(False)

    def cancel(self):
        if self.job:self.job.cancel.set()
        self.client.cancel();self.status.setText('已取消；模型服务可能仍会结算已发出的请求。')

    def shutdown(self):
        if self.job:self.job.cancel.set()
        self.client.cancel()
