"""Unit tests for configuration; no live provider requests."""
import pytest
from web_search_mcp.web_search_config import connection

@pytest.fixture(autouse=True)
def config(monkeypatch):
    for name in ('WEB_SEARCH_AUTH_MODE','WEB_SEARCH_API_KEY','TAVILY_API_KEY',
                 'WEB_SEARCH_AUTH_HEADER','WEB_SEARCH_AUTH_PREFIX'):
        monkeypatch.delenv(name,raising=False)
    monkeypatch.setenv('WEB_SEARCH_MCP_URL','https://mcp.tavily.com/mcp/')
    monkeypatch.setenv('WEB_SEARCH_TRANSPORT','http')


def test_keyless_ignores_old_keys(monkeypatch):
    monkeypatch.setenv('WEB_SEARCH_AUTH_MODE','keyless')
    monkeypatch.setenv('TAVILY_API_KEY','old-test-key')
    monkeypatch.setenv('WEB_SEARCH_API_KEY','other-test-key')
    monkeypatch.setenv('WEB_SEARCH_AUTH_HEADER','X-API-Key')
    assert connection()['headers']=={'X-Tavily-Access-Mode':'keyless'}


def test_api_key_default_unchanged(monkeypatch):
    monkeypatch.setenv('TAVILY_API_KEY','test-key')
    assert connection()['headers']=={'Authorization':'Bearer test-key'}


def test_generic_key_priority(monkeypatch):
    monkeypatch.setenv('TAVILY_API_KEY','tavily-test')
    monkeypatch.setenv('WEB_SEARCH_API_KEY','generic-test')
    assert connection()['headers']=={'Authorization':'Bearer generic-test'}


def test_blank_url_disables_search(monkeypatch):
    monkeypatch.setenv('WEB_SEARCH_AUTH_MODE','keyless')
    monkeypatch.setenv('WEB_SEARCH_MCP_URL','')
    assert connection() is None

@pytest.mark.parametrize('url',[
    'http://mcp.tavily.com/mcp/',
    'https://example.org/mcp/',
    'https://mcp.tavily.com/mcp/?tavilyApiKey=test',
    'https://user:password@mcp.tavily.com/mcp/',
    'https://mcp.tavily.com/other',
])
def test_keyless_rejects_wrong_or_credentialed_url(monkeypatch,url):
    monkeypatch.setenv('WEB_SEARCH_AUTH_MODE','keyless')
    monkeypatch.setenv('WEB_SEARCH_MCP_URL',url)
    with pytest.raises(ValueError):connection()

@pytest.mark.parametrize('setting,value',[
    ('WEB_SEARCH_AUTH_MODE','unknown'),
    ('WEB_SEARCH_TRANSPORT','sse'),
])
def test_bad_mode_or_transport(monkeypatch,setting,value):
    monkeypatch.setenv('WEB_SEARCH_AUTH_MODE','keyless')
    monkeypatch.setenv(setting,value)
    with pytest.raises(ValueError):connection()


def test_quota_response_is_not_success():
    from scripts.smoke_test import validate_search_result
    with pytest.raises(RuntimeError, match='Daily cap'):
        validate_search_result({'code':'daily_cap_reached','message':'Daily cap reached'})


def test_real_results_are_accepted():
    from scripts.smoke_test import validate_search_result
    assert validate_search_result({'results':[]}) == {'results':[]}


def test_unknown_response_is_not_success():
    from scripts.smoke_test import validate_search_result
    with pytest.raises(RuntimeError):validate_search_result({'message':'No access'})
