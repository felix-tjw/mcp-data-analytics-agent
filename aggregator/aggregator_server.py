"""One HTTP MCP endpoint proxying two local STDIO servers and optional remote search."""
import os
import sys
from fastmcp import FastMCP
from config import settings
from web_search_mcp.web_search_config import connection

def create_server():
    env = dict(os.environ)
    env['PYTHONPATH'] = str(settings.ROOT) + os.pathsep + env.get('PYTHONPATH','')
    servers = {
        'pandas': {'command': sys.executable, 'args': ['-m','pandas_mcp.pandas_server'], 'env': env},
        'rag': {'command': sys.executable, 'args': ['-m','rag_mcp.rag_server'], 'env': env},
    }
    # Optional administrator-supplied STDIO adapter for an existing RAG implementation.
    if os.getenv('RAG_SERVER_SCRIPT'):
        servers['rag']['args'] = [str(settings.path('RAG_SERVER_SCRIPT', ''))]
    remote = connection()
    if remote: servers['web'] = remote
    return FastMCP.as_proxy({'mcpServers': servers}, name='Analytics MCP Aggregator')

if __name__ == '__main__':
    create_server().run(transport='http', host=settings.AGGREGATOR_HOST, port=settings.AGGREGATOR_PORT, show_banner=False)
