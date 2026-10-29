import threading
import time

from workbuddy_pet.runtime import RuntimeWriter


def test_writer_is_background_coalesces_and_flushes_latest_on_close(tmp_path):
    entered=threading.Event();release=threading.Event();writes=[];threads=[]
    def write(path,value):
        threads.append(threading.get_ident());entered.set();release.wait(2);writes.append(value)
    writer=RuntimeWriter(tmp_path/'runtime.json',write=write)
    try:
        writer.submit({'version':'0.6.6','state':'idle','at':1})
        assert entered.wait(2)
        for i in range(100):writer.submit({'version':'0.6.6','state':'working','sequence':i,'at':i})
        assert not writes  # submit did not wait for disk.
        release.set()
    finally:writer.close()
    assert len(writes)==2 and writes[-1]['sequence']==99
    assert all(t!=threading.get_ident() for t in threads)
    assert writes[0]['at']>1


def test_writer_ignores_timestamp_only_changes_but_keeps_heartbeat(tmp_path):
    written=threading.Event();writes=[]
    def write(path,value):writes.append(value);written.set()
    writer=RuntimeWriter(tmp_path/'runtime.json',write=write,heartbeat=.15)
    try:
        writer.submit({'state':'idle','at':1});assert written.wait(2);written.clear()
        for i in range(50):writer.submit({'state':'idle','at':i+2})
        assert not written.wait(.05)
        assert written.wait(1)
    finally:writer.close()
    assert 2<=len(writes)<=3


def test_failed_write_retries_without_new_state(tmp_path):
    complete=threading.Event();calls=[]
    def write(path,value):
        calls.append(value)
        if len(calls)==1:raise OSError('synthetic locked file')
        complete.set()
    writer=RuntimeWriter(tmp_path/'runtime.json',write=write,retry_delay=.02)
    try:
        writer.submit({'state':'idle'});assert complete.wait(2)
    finally:writer.close()
    assert len(calls)==2
