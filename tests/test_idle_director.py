import random
from dataclasses import replace

from workbuddy_pet.interaction import IdleDirector, idle_allowed, response_for_click
from workbuddy_pet.materials import CLICK_ACTIONS, LEISURE_ACTIONS
from workbuddy_pet.state import DisplayState, SessionState


def test_idle_random_delay_duration_no_repeat_and_cancel():
    director=IdleDirector(random.Random(7))
    assert director.step(100,True) is None and 118<=director.next_due<=140
    previous=None
    for _ in range(15):
        now=director.next_due
        action=director.step(now,True)
        assert action.action in LEISURE_ACTIONS and action.action!=previous and 6<=action.seconds<=10
        assert director.step(now+1,True)==action
        previous=action.action
        assert director.step(director.until,True) is None
        assert 18<=director.next_due-director.until<=40
    director.step(director.next_due,True)
    assert director.step(director.until-1,False) is None and director.active is None and director.next_due is None
    director.step(1000,True);assert 1018<=director.next_due<=1040


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


def test_stale_session_does_not_starve_random_idle():
    from workbuddy_pet.state import derive_display
    old={'old':SessionState('old','working',at=100)}
    assert idle_allowed(old,derive_display(old,220),220)
    assert old['old'].state=='working' and not old['old'].terminal
    old['approval']=SessionState('approval','review',at=0)
    assert not idle_allowed(old,derive_display(old,9999),9999)

def test_supported_pool_and_authored_finish_schedule():
    d=IdleDirector(random.Random(2));d.next_due=0
    assert d.step(0,True,('idle_sleep',)).action=='idle_sleep'
    d.finish(3.6)
    assert d.active is None and 21.6<=d.next_due<=43.6
    assert d.step(d.next_due,True,()) is None
    d.next_due=0
    assert d.step(100,True,('idle_bow',)).action=='idle_bow'
