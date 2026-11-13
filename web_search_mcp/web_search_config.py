"""Remote MCP connection supporting API-key authentication and Tavily keyless access."""
import os
from urllib.parse import urlparse


def connection():
    url = os.getenv('WEB_SEARCH_MCP_URL', '').strip()
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme != 'https':
        raise ValueError('Remote web search must use HTTPS.')
    transport = os.getenv('WEB_SEARCH_TRANSPORT', 'http').strip().lower()
    if transport not in {'http', 'sse'}:
        raise ValueError('WEB_SEARCH_TRANSPORT must be http or sse.')
    mode = os.getenv('WEB_SEARCH_AUTH_MODE', 'api_key').strip().lower()
    if mode not in {'api_key', 'keyless'}:
        raise ValueError('WEB_SEARCH_AUTH_MODE must be api_key or keyless.')

    if mode == 'keyless':
        # Do not accidentally send credentials in the URL or to a different provider.
        if (parsed.hostname != 'mcp.tavily.com' or parsed.path.rstrip('/') != '/mcp'
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.port not in (None, 443)):
            raise ValueError('Tavily keyless mode requires https://mcp.tavily.com/mcp/ without URL credentials or query parameters.')
        if transport != 'http':
            raise ValueError('Tavily keyless mode requires WEB_SEARCH_TRANSPORT=http (Streamable HTTP).')
        # Deliberately ignore both key variables and custom authentication settings.
        # A Bearer key would override keyless access at the provider.
        headers = {'X-Tavily-Access-Mode': 'keyless'}
    else:
        key = os.getenv('WEB_SEARCH_API_KEY') or os.getenv('TAVILY_API_KEY')
        headers = {}
        if key:
            header = os.getenv('WEB_SEARCH_AUTH_HEADER', 'Authorization')
            prefix = os.getenv('WEB_SEARCH_AUTH_PREFIX', 'Bearer ')
            headers[header] = prefix + key
    return {'url': url, 'transport': transport, 'headers': headers}
