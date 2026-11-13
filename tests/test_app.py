import io
import pytest
import app as module
from app import create_app
@pytest.fixture
def web(storage):
    a=create_app();a.config['TESTING']=True;return a

def csrf(c):
    c.get('/')
    with c.session_transaction() as s:return {'X-CSRF-Token':s['csrf']}

def activate(c,headers):
    r=c.post('/api/upload',data={'file':(io.BytesIO(b'name,amount\na,10\nb,20\n'),'sample.csv')},headers=headers)
    assert r.status_code==200
    r=c.post('/api/activate',json={'header_row':1,'sheet':'CSV'},headers=headers)
    assert r.status_code==200
    return r.json['dataset']['dataset_id']

def test_upload_and_isolation(web,monkeypatch):
    one=web.test_client();two=web.test_client();h=csrf(one);h2=csrf(two)
    first=activate(one,h)
    assert two.get('/api/dataset').json['dataset'] is None
    assert two.post('/api/tool',json={'tool':'pandas_get_dataset_info'},headers=h2).status_code==400
    async def fake_call(name,args):return args
    monkeypatch.setattr(module.mcp_client,'call',fake_call)
    result=one.post('/api/tool',json={'tool':'pandas_get_dataset_info','arguments':{'dataset_id':'foreign'}},headers=h)
    assert result.json['result']['dataset_id']==first

def test_bad_upload_and_csrf(web):
    c=web.test_client();h=csrf(c)
    assert c.post('/api/upload').status_code==403
    assert c.post('/api/upload',data={'file':(io.BytesIO(b'x'),'x.exe')},headers=h).status_code==400
    assert c.post('/api/upload',data={'file':(io.BytesIO(b'not excel'),'x.xlsx')},headers=h).status_code==400

def test_chat_missing_config(web,monkeypatch):
    monkeypatch.delenv('OPENROUTER_API_KEY',raising=False);monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    c=web.test_client();h=csrf(c);activate(c,h)
    r=c.post('/api/chat',json={'question':'How many rows?'},headers=h)
    assert r.status_code==400 and 'MODEL' in r.json['error']
