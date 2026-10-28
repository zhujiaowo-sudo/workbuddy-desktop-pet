from dataclasses import replace
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from test_detached_capsule import controller_for


def test_summary_minus_only_collapses_card_and_keeps_avatar(tmp_path,qt_app):
    controller=controller_for(tmp_path,qt_app)
    try:
        controller.open_card();assert controller.pet.isVisible()
        QTest.mouseClick(controller.bubble.collapse_button,Qt.MouseButton.LeftButton)
        assert controller.bubble.compact and controller.pet.isVisible() and not controller.avatar_collapsed
        assert not controller.settings.avatar_collapsed and controller.settings.compact
        assert controller.bubble.show_avatar_action.text()=='收成胶囊'
    finally:controller.shutdown()


def test_single_menu_toggle_switches_label_and_restores_without_duplicate(tmp_path,qt_app):
    controller=controller_for(tmp_path,qt_app)
    try:
        for _ in range(3):
            action=controller.bubble.show_avatar_action
            assert action.text()=='收成胶囊'
            action.trigger();assert not controller.pet.isVisible() and action.text()=='显示桌宠'
            labels=[a.text() for a in controller.bubble.context_menu.actions()]
            assert labels.count('显示桌宠')==1 and '收成胶囊' not in labels
            action.trigger();assert controller.pet.isVisible() and action.text()=='收成胶囊'
            assert not controller.avatar_collapsed and controller.bubble.compact
        controller.apply_settings(replace(controller.settings,card_only=True))
        action.trigger();assert not controller.settings.card_only and controller.pet.isVisible()
    finally:controller.shutdown()
