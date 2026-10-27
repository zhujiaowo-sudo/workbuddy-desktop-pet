import base64,json
import pytest
from workbuddy_pet import checkin
from workbuddy_pet.workbuddy_relay import request_json,RelayError,_proof,PIPE_PREFIX


@pytest.mark.parametrize('purpose,path',[('balance','/billing/meter/get-user-resource-summary'),
    ('checkin_status','/v2/billing/meter/checkin-activity-status'),('checkin_claim','/v2/billing/meter/daily-checkin')])
def test_fixed_relay_purposes_and_no_ticket_leak(tmp_path,purpose,path):
    ticket='synthetic-ticket-not-a-real-secret';endpoint=PIPE_PREFIX+'synthetic123';sent=[]
    (tmp_path/'wbipc').mkdir();(tmp_path/'wbipc/endpoint.json').write_text(json.dumps({'ticket':ticket,'endpoint':endpoint}))
    class Pipe:
        def __init__(self,address):assert address==endpoint;self.step=0
        def send(self,value):sent.append(value)
        def receive(self):
            self.step+=1
            if self.step==1:return {'type':'session_challenge','server_nonce':'synthetic-server-nonce',
                'server_proof':_proof(ticket,'server',endpoint,sent[0]['client_nonce'],'synthetic-server-nonce')}
            if self.step==2:return {'type':'session_hello_ack','pipes':['wb.request']}
            if self.step==3:return {'id':1,'result':{'channel':'c:wb.request','methods':['http.fetch']}}
            return {'id':2,'result':{'status':200,'body_b64':base64.b64encode(b'{"code":0}').decode()}}
        def close(self):pass
    assert request_json(tmp_path,purpose,Pipe)=={'code':0}
    assert sent[-1]['params']['path']==path and sent[-1]['params']['method']=='POST'
    assert base64.b64decode(sent[-1]['params']['body_b64'])==b'{}'
    assert ticket not in json.dumps(sent) and 'authorization' not in json.dumps(sent).lower()
    with pytest.raises(RelayError):request_json(tmp_path/'does-not-exist','https://example.com')


def test_status_and_claim_do_not_invent_rewards():
    result=checkin.parse_status({'code':0,'data':{'active':True,'today_checked_in':False,'daily_credit':10}})
    assert result.state=='available' and result.daily_credit==10
    assert checkin.parse_status({'code':0,'data':{'active':True,'today_checked_in':True}}).checked
    assert checkin.parse_status({'code':0,'data':{'active':False,'today_checked_in':False}}).state=='inactive'
    for bad in ({'code':401},{'code':0,'data':{}},{'code':0,'data':{'active':True,'today_checked_in':'false'}}):
        with pytest.raises(checkin.CheckinError):checkin.parse_status(bad)
    claimed=checkin.parse_claim({'code':0,'data':{'credit':12.5}})
    assert claimed.state=='claimed' and claimed.awarded==12.5 and claimed.checked
    assert checkin.parse_claim({'code':0,'data':{}}).awarded is None
    assert checkin.parse_claim({'code':1001}).checked
    for code in (1002,1003):assert checkin.parse_claim({'code':code}).state=='inactive'
    assert checkin.parse_claim({'code':9999}).state=='error'


def test_click_checks_status_before_claim_and_never_retries(tmp_path,monkeypatch):
    calls=[]
    def query(home,purpose):
        calls.append(purpose)
        return {'code':0,'data':{'active':True,'today_checked_in':False}} if purpose=='checkin_status' else {'code':0,'data':{'credit':10}}
    monkeypatch.setattr(checkin,'request_json',query)
    assert checkin.perform_checkin(tmp_path).state=='claimed'
    assert calls==['checkin_status','checkin_claim']

    calls.clear()
    def already(home,purpose):calls.append(purpose);return {'code':0,'data':{'active':True,'today_checked_in':True}}
    monkeypatch.setattr(checkin,'request_json',already)
    assert checkin.perform_checkin(tmp_path).checked and calls==['checkin_status']
    calls.clear();monkeypatch.setattr(checkin,'request_json',query)
    assert checkin.perform_checkin(tmp_path,cancel=lambda:True).state=='unknown' and not calls
    def interrupted(home,purpose):
        if purpose=='checkin_status':return query(home,purpose)
        calls.append(purpose);raise RelayError('synthetic timeout')
    monkeypatch.setattr(checkin,'request_json',interrupted)
    assert checkin.perform_checkin(tmp_path).state=='uncertain'
    assert calls==['checkin_status','checkin_claim']


def test_cancellation_after_status_prevents_claim(tmp_path,monkeypatch):
    calls=[];cancelled=False
    def query(home,purpose):
        nonlocal cancelled
        calls.append(purpose);cancelled=True
        return {'code':0,'data':{'active':True,'today_checked_in':False}}
    monkeypatch.setattr(checkin,'request_json',query)
    result=checkin.perform_checkin(tmp_path,cancel=lambda:cancelled)
    assert calls==['checkin_status'] and not result.checked and result.awarded is None
