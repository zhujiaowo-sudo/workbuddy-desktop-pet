import base64,json
import pytest
from workbuddy_pet.balance import BalanceError,parse_summary,_summary,_proof,PIPE_PREFIX,SUMMARY_PATH,read_balance


def test_summary_precision_zero_and_incomplete_data():
    data={'code':0,'data':{'Packages':[{'CycleRemainCapacity':'1.23'},{'CycleRemainCapacity':2.34}]}}
    assert parse_summary(data,at=1).remaining==3.57
    assert parse_summary({'code':0,'data':{'Packages':[]}}).remaining==0
    for packages in (None,[{}],[{'CycleRemainCapacity':-1}],[{'CycleRemainCapacity':True}],[{'CycleRemainCapacity':'nan'}]):
        with pytest.raises(BalanceError):parse_summary({'code':0,'data':{'Packages':packages}})
    with pytest.raises(BalanceError):parse_summary({'code':401})


def test_mutual_proof_and_only_credit_query_without_ticket_leak(tmp_path):
    endpoint=PIPE_PREFIX+'synthetic123';ticket='synthetic-ticket-not-a-real-secret'
    (tmp_path/'wbipc').mkdir();(tmp_path/'wbipc/endpoint.json').write_text(json.dumps({'endpoint':endpoint,'ticket':ticket}))
    sent=[]
    class FakePipe:
        def __init__(self,address):assert address==endpoint;self.step=0
        def send(self,value):sent.append(value)
        def receive(self):
            self.step+=1
            if self.step==1:
                return {'type':'session_challenge','server_nonce':'synthetic-server-nonce',
                    'server_proof':_proof(ticket,'server',endpoint,sent[0]['client_nonce'],'synthetic-server-nonce')}
            if self.step==2:return {'type':'session_hello_ack','pipes':['wb.request']}
            if self.step==3:return {'id':1,'result':{'channel':'c:wb.request','methods':['http.fetch']}}
            return {'id':2,'result':{'status':200,'body_b64':base64.b64encode(b'{"code":0,"data":{"Packages":[]}}').decode()}}
        def close(self):pass
    assert _summary(tmp_path,FakePipe)['code']==0
    assert sent[-1]['params']['path']==SUMMARY_PATH
    assert sent[-1]['params']['method']=='POST' and base64.b64decode(sent[-1]['params']['body_b64'])==b'{}'
    assert ticket not in json.dumps(sent)
    assert all('authorization' not in str(value).lower() for value in sent)


def test_missing_host_and_untrusted_server_fail_closed(tmp_path):
    assert read_balance(tmp_path).remaining is None
    (tmp_path/'wbipc').mkdir();(tmp_path/'wbipc/endpoint.json').write_text(json.dumps({'endpoint':PIPE_PREFIX+'synthetic123','ticket':'synthetic-ticket'}))
    class BadServer:
        def __init__(self,address):pass
        def send(self,value):pass
        def receive(self):return {'type':'session_challenge','server_nonce':'synthetic-server-nonce','server_proof':'wrong'}
        def close(self):pass
    with pytest.raises(BalanceError):_summary(tmp_path,BadServer)


def test_disabled_balance_never_reads_local_ticket(tmp_path,qt_app,monkeypatch):
    from workbuddy_pet.app import Controller
    import workbuddy_pet.app as application
    calls=[]
    monkeypatch.setattr(application,'read_balance',lambda home:calls.append(home))
    controller=Controller(qt_app,tmp_path,False,workbuddy_home=tmp_path/'absent')
    controller.load_balance();qt_app.processEvents()
    assert not calls and controller.bubble.balance_badge.text()=='积分未启用'
    controller.shutdown()


def test_enabled_balance_updates_badge_without_persisting_amount(tmp_path,qt_app,monkeypatch):
    from workbuddy_pet.app import Controller
    from workbuddy_pet.settings import Settings,save_settings
    from workbuddy_pet.balance import BalanceSnapshot
    from PySide6.QtTest import QTest
    import workbuddy_pet.app as application
    monkeypatch.setattr(application,'read_balance',lambda home:BalanceSnapshot(123.45,1,'synthetic source'))
    save_settings(tmp_path,Settings(balance_enabled=True,notifications=False))
    controller=Controller(qt_app,tmp_path,False,workbuddy_home=tmp_path/'absent')
    import time
    deadline=time.monotonic()+3
    while time.monotonic()<deadline and (controller.bubble.balance is None or not (tmp_path/'runtime.json').is_file()):
        qt_app.processEvents();time.sleep(.01)
    assert controller.bubble.balance==123.45
    assert controller.bubble.balance_badge.text()=='123'
    assert '123.45' not in (tmp_path/'settings.json').read_text()
    assert '123.45' not in (tmp_path/'runtime.json').read_text()
    controller.shutdown()
