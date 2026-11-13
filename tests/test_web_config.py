import pytest
from web_search_mcp.web_search_config import connection

def test_remote_auth_and_transport(monkeypatch):
    monkeypatch.setenv('WEB_SEARCH_MCP_URL','https://mcp.tavily.com/mcp/')
    monkeypatch.setenv('TAVILY_API_KEY','test-placeholder')
    monkeypatch.delenv('WEB_SEARCH_API_KEY',raising=False)
    monkeypatch.setenv('WEB_SEARCH_TRANSPORT','http')
    assert connection()['headers']['Authorization']=='Bearer test-placeholder'
    monkeypatch.setenv('WEB_SEARCH_MCP_URL','http://remote.example/mcp')
    with pytest.raises(ValueError):connection()
    monkeypatch.setenv('WEB_SEARCH_MCP_URL','')
    assert connection() is None
