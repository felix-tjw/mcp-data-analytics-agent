"""Real HTTP aggregator -> STDIO subprocesses; no live LLM/search credentials needed."""
import asyncio
import os
import socket
import subprocess
import sys
import pandas as pd
import pytest
from fastmcp import Client
from langchain_mcp_adapters.client import MultiServerMCPClient
from config import settings
from services.datasets import save_dataset

@pytest.mark.integration
async def test_aggregator_stdio_and_http(storage,monkeypatch):
    df=pd.DataFrame({'Module':['Debt','Debt','API'],'Effort':[2,4,8]})
    dataset=save_dataset(df,{'name':'integration.csv'})['dataset_id']
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env=dict(os.environ,AGGREGATOR_PORT=str(port),UPLOAD_FOLDER=str(settings.UPLOAD_FOLDER),
             VECTOR_STORE_PATH=str(settings.VECTOR_STORE_PATH),RAG_BACKEND='tfidf',WEB_SEARCH_MCP_URL='',RAG_SERVER_SCRIPT='')
    proc=subprocess.Popen([sys.executable,'-m','aggregator.aggregator_server'],cwd=settings.ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    url=f'http://127.0.0.1:{port}/mcp'
    try:
        ready=False
        for _ in range(100):
            try:
                reader,writer=await asyncio.open_connection('127.0.0.1',port)
                writer.close();await writer.wait_closed();ready=True;break
            except OSError: await asyncio.sleep(.1)
        assert ready,'Aggregator failed to start'
        async with Client(url,timeout=60) as c:
            names={t.name for t in await c.list_tools()}
            assert names=={'pandas_get_dataset_info','pandas_get_column_summary','pandas_aggregate_data',
                           'pandas_groupby_data','pandas_filter_dataset','pandas_compare_dates','rag_rag_load_dataset','rag_rag_search_dataset','rag_rag_get_dataset_info'}
            result=await c.call_tool('pandas_groupby_data',{'dataset_id':dataset,'group_by':['Module'],'aggregations':{'Effort':'sum'}})
            assert result.data['total_groups']==2
            result=await c.call_tool('rag_rag_search_dataset',{'dataset_id':dataset,'query':'Debt'})
            assert len(result.data['matches'])==2
            # Fresh HTTP client still sees the persisted dataset and index.
        adapter=MultiServerMCPClient({'analytics':{'url':url,'transport':'streamable_http'}})
        tools=await adapter.get_tools()
        tool=next(t for t in tools if t.name=='pandas_aggregate_data')
        result=await tool.ainvoke({'dataset_id':dataset,'function':'sum','column_name':'Effort'})
        assert '14' in str(result)
        # Exercise actual LangChain tool execution with a scripted model, never a paid API call.
        from langchain_core.language_models.chat_models import BaseChatModel
        from langchain_core.messages import AIMessage
        from langchain_core.outputs import ChatGeneration, ChatResult
        from agent import ai_agent
        class ScriptedModel(BaseChatModel):
            @property
            def _llm_type(self): return 'scripted-test'
            def bind_tools(self,tools,**kwargs): return self
            def _generate(self,messages,stop=None,run_manager=None,**kwargs):
                count=sum(getattr(m,'type','')=='tool' for m in messages)
                if count == 0:
                    msg=AIMessage(content='',tool_calls=[{'name':'pandas_aggregate_data','args':{'function':'sum','column_name':'Effort'},'id':'calc','type':'tool_call'}])
                elif count == 1:
                    msg=AIMessage(content='',tool_calls=[{'name':'rag_rag_search_dataset','args':{'query':'Debt'},'id':'retrieve','type':'tool_call'}])
                else: msg=AIMessage(content='Scripted test completed: calculation and retrieval both returned evidence.')
                return ChatResult(generations=[ChatGeneration(message=msg)])
        async def discover(): return tools
        monkeypatch.setattr(ai_agent,'available_tools',discover)
        monkeypatch.setattr(ai_agent,'ChatOpenAI',lambda **kwargs:ScriptedModel())
        monkeypatch.setenv('OPENAI_API_KEY','scripted-test-no-network')
        monkeypatch.setenv('MODEL','scripted-test')
        response=await ai_agent.answer('Total effort and relevant Debt records',dataset)
        assert [t['tool'] for t in response['tool_results']]==['pandas_aggregate_data','rag_rag_search_dataset']
        # Complete Flask -> agent -> HTTP aggregator -> STDIO workflow, using an actual uploaded file.
        from agent import mcp_client
        from app import create_app
        import io
        monkeypatch.setattr(mcp_client,'AGGREGATOR_URL',url)
        def flask_workflow():
            web=create_app().test_client();web.get('/')
            with web.session_transaction() as state:headers={'X-CSRF-Token':state['csrf']}
            uploaded=web.post('/api/upload',data={'file':(io.BytesIO(df.to_csv(index=False).encode()),'workflow.csv')},headers=headers)
            assert uploaded.status_code==200
            activated=web.post('/api/activate',json={'header_row':1,'sheet':'CSV'},headers=headers)
            assert activated.status_code==200 and activated.json['dataset']['rows']==3
            result=web.post('/api/tool',json={'tool':'pandas_aggregate_data','arguments':{'function':'sum','column_name':'Effort'}},headers=headers)
            assert result.status_code==200 and result.json['result']['value']==14
            chat=web.post('/api/chat',json={'question':'Total effort and Debt context'},headers=headers)
            assert chat.status_code==200 and len(chat.json['tool_results'])==2
        await asyncio.to_thread(flask_workflow)


    finally:
        proc.terminate()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
