import asyncio
from fastmcp import Client
from langchain_mcp_adapters.client import MultiServerMCPClient
from config.settings import AGGREGATOR_URL, TOOL_TIMEOUT

def client():
    return MultiServerMCPClient({'analytics': {'url': AGGREGATOR_URL, 'transport': 'streamable_http'}})

async def available_tools():
    return await asyncio.wait_for(client().get_tools(), timeout=TOOL_TIMEOUT)

async def call(name, arguments):
    async with Client(AGGREGATOR_URL, timeout=TOOL_TIMEOUT) as c:
        result = await c.call_tool(name, arguments)
        if result.is_error: raise ValueError('The MCP tool returned an error.')
        return result.data

async def health():
    async with Client(AGGREGATOR_URL, timeout=10) as c:
        tools = await c.list_tools()
        return [t.name for t in tools]
