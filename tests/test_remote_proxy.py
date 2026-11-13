"""Test the remote-provider HTTP proxy contract using a local fake search MCP service.
This is not evidence of a successful live Tavily request.
"""
import asyncio
import os
import socket
import subprocess
import sys
import pytest
from fastmcp import Client
from config import settings

def free_port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

async def ready(port,proc):
    for _ in range(100):
        if proc.poll() is not None:raise AssertionError('MCP test process exited')
        try:
            _,w=await asyncio.open_connection('127.0.0.1',port);w.close();await w.wait_closed();return
        except OSError:await asyncio.sleep(.1)
    raise AssertionError('MCP service did not start')

@pytest.mark.integration
async def test_remote_http_proxy(storage):
    remote_port=free_port(); proxy_port=free_port()
    source=f'''from fastmcp import FastMCP
m=FastMCP("Fake Search")
@m.tool
def search(query:str)->dict:
    """Return synthetic search evidence for integration testing."""
    return {{"results":[{{"title":"Test source","url":"https://example.org/test","content":query}}]}}
m.run(transport="http",host="127.0.0.1",port={remote_port},show_banner=False)
'''
    remote=subprocess.Popen([sys.executable,'-c',source],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    proxy=None
    try:
        await ready(remote_port,remote)
        # Inject a local test transport without weakening production HTTPS validation.
        bridge=f'''from aggregator import aggregator_server as a
a.connection=lambda:{{"url":"http://127.0.0.1:{remote_port}/mcp","transport":"http"}}
a.create_server().run(transport="http",host="127.0.0.1",port={proxy_port},show_banner=False)
'''
        env=dict(os.environ,UPLOAD_FOLDER=str(settings.UPLOAD_FOLDER),VECTOR_STORE_PATH=str(settings.VECTOR_STORE_PATH),RAG_SERVER_SCRIPT='')
        proxy=subprocess.Popen([sys.executable,'-c',bridge],cwd=settings.ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        await ready(proxy_port,proxy)
        async with Client(f'http://127.0.0.1:{proxy_port}/mcp') as client:
            names={t.name for t in await client.list_tools()}
            assert len(names)==10 and 'web_search' in names
            result=await client.call_tool('web_search',{'query':'generic delivery practices'})
            assert result.data['results'][0]['content']=='generic delivery practices'
    finally:
        for proc in (proxy,remote):
            if proc:
                proc.terminate()
                try:proc.wait(timeout=10)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
