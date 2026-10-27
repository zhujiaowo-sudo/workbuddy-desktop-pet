from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from workbuddy_pet.state import DisplayState, Reminder
from workbuddy_pet.ui.pet import PetWindow, StatusBubble


def test_click_and_drag_are_distinct(qt_app):
    pet = PetWindow()
    opened = []
    pet.open_requested.connect(lambda: opened.append(True))
    pet.show()
    QTest.mouseClick(pet, Qt.MouseButton.LeftButton, pos=QPoint(80, 90))
    assert len(opened) == 1
    QTest.mousePress(pet, Qt.MouseButton.LeftButton, pos=QPoint(80, 90))
    QTest.mouseMove(pet, QPoint(110, 110))
    QTest.mouseRelease(pet, Qt.MouseButton.LeftButton, pos=QPoint(110, 110))
    assert len(opened) == 1
    pet.close()


def test_disconnected_and_ack_visibility(qt_app):
    bubble = StatusBubble()
    bubble.show()
    assert "等待 WorkBuddy 连接" in bubble.title.text()
    reminder = Reminder("one", "s", "done")
    display = DisplayState("done", "connected", "s", (reminder,), 1)
    bubble.set_display(display)
    bubble.set_display(display)
    assert bubble.ack.isVisible()
    assert "任务完成" in bubble.title.text()
    bubble.set_display(DisplayState("idle", "connected"))
    assert not bubble.ack.isVisible()
    bubble.close()
