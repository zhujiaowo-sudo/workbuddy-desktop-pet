import random
from dataclasses import replace

from workbuddy_pet.interaction import IdleDirector, idle_allowed, response_for_click
from workbuddy_pet.materials import CLICK_ACTIONS, LEISURE_ACTIONS
from workbuddy_pet.state import DisplayState, SessionState


def test_idle_random_delay_duration_no_repeat_and_cancel():
    director=IdleDirector(random.Random(7))
    assert director.step(100,True) is None and 145<=director.next_due<=210
    previous=None
    for _ in range(15):
        now=director.next_due
        action=director.step(now,True)
        assert action.action in LEISURE_ACTIONS and action.action!=previous and 6<=action.seconds<=10
        assert director.step(now+1,True)==action
        previous=action.action
        assert director.step(director.until,True) is None
        assert 45<=director.next_due-director.until<=110
    director.step(director.next_due,True)
    assert director.step(director.until-1,False) is None and director.active is None and director.next_due is None
    director.step(1000,True);assert 1045<=director.next_due<=1110


def test_all_sessions_and_done_grace_control_idle():
    display=DisplayState('done','connected')
    sessions={'done':SessionState('done','done',at=100,terminal=True)}
    assert not idle_allowed(sessions,display,111)
    assert idle_allowed(sessions,display,112)
    for state in ('working','thinking','waiting','review','failed'):
        busy=replace(sessions['done'],session_id='peer',state=state)
        assert not idle_allowed({**sessions,'peer':busy},display,200)
    assert idle_allowed({},DisplayState(),0)


def test_clicks_have_four_independent_expressions():
    assert tuple(response_for_click(i).action for i in range(4))==CLICK_ACTIONS
    assert response_for_click(4)==response_for_click(0)
