"""Quiet desktop-tool surfaces, shared by the dashboard and dialogs."""
from pathlib import Path
ICON_ROOT=(Path(__file__).resolve().parents[1]/'assets/ui').as_posix()
STYLE = '''
QWidget { font-family: "Microsoft YaHei UI", "Segoe UI"; font-size:12px; color:#202020; }
QDialog { background:#ffffff; }
QLabel { background:transparent; }
QPushButton { background:#ffffff; color:#262626; border:1px solid rgba(0,0,0,24);
 border-radius:6px; padding:6px 9px; }
QPushButton:hover { background:#f5f5f5; border-color:#d4d4d4; }
QPushButton:pressed { background:#ebebeb; }
QPushButton:focus { border-color:#737373; }
QPushButton:disabled { color:#a0a0a0; background:#fafafa; }
QPushButton[primary="true"] { background:#202020; border-color:#202020; color:white; }
QPushButton[primary="true"]:hover { background:#3a3a3a; }
QLineEdit,QTextEdit,QSpinBox,QComboBox { background:white; color:#202020;
 border:1px solid #e0e0e0; border-radius:4px; padding:6px; selection-background-color:#e8e8e8; }
QComboBox::drop-down { subcontrol-origin:padding; subcontrol-position:top right; width:24px; border:0; }
QSpinBox::up-button,QSpinBox::down-button { width:20px; border:0; background:transparent; }
QComboBox::down-arrow { image:url(__ICONS__/chevron-down.svg); width:10px; height:7px; }
QSpinBox::down-arrow { image:url(__ICONS__/chevron-down.svg); width:8px; height:5px; }
QSpinBox::up-arrow { image:url(__ICONS__/chevron-up.svg); width:8px; height:5px; }
QComboBox QAbstractItemView { background:white; color:#202020; selection-background-color:#f0f0f0; }
QCheckBox { spacing:7px; padding:3px 0; }
QTabBar::tab { background:transparent; color:#737373; padding:8px 10px;
 border-bottom:2px solid transparent; }
QTabBar::tab:selected { color:#202020; border-bottom:2px solid #202020; }
QTabBar::tab:hover { background:#f7f7f7; }
QTableWidget { background:white; alternate-background-color:#fafafa;
 border:1px solid #e8e8e8; selection-background-color:#efefef; selection-color:#202020; }
QHeaderView::section { background:#f7f7f7; color:#737373; padding:7px; border:0; }
QScrollBar:vertical { background:transparent; width:7px; margin:1px; }
QScrollBar::handle:vertical { background:#d0d0d0; border-radius:3px; min-height:25px; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height:0px; }
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical { background:transparent; }
QToolTip { color:#262626; background:#ffffff; border:1px solid #e0e0e0; padding:5px; }
'''

STYLE=STYLE.replace('__ICONS__',ICON_ROOT)
MENU = '''QMenu { background:#ffffff; color:#262626; border:1px solid rgba(0,0,0,24); padding:5px; font-size:12px; }
QMenu::item { padding:8px 25px 8px 18px; border-radius:4px; }
QMenu::item:selected { background:#f0f0f0; }
QMenu::separator { height:1px; background:#ececec; margin:5px 8px; }'''
