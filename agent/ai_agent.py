import asyncio
import copy
import json
import os
from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from agent.mcp_client import available_tools
from config.prompts import SYSTEM_PROMPT
from config.settings import CHAT_TIMEOUT

class ConfigurationError(ValueError): pass

def scoped_tools(tools, dataset_id):
    """Remove dataset_id from model schemas and bind it in code, not merely in the prompt."""
    result = []
    for original in tools:
        schema = original.args_schema
        schema = copy.deepcopy(schema if isinstance(schema,dict) else schema.model_json_schema())
        if 'dataset_id' not in schema.get('properties',{}):
            result.append(original); continue
        schema['properties'].pop('dataset_id')
        schema['required'] = [k for k in schema.get('required',[]) if k != 'dataset_id']
        async def invoke(_tool=original, **kwargs):
            kwargs['dataset_id'] = dataset_id
            return await _tool.ainvoke(kwargs)
        result.append(StructuredTool(name=original.name, description=original.description,
                                     args_schema=schema, coroutine=invoke))
    return result

async def answer(question, dataset_id, history=None):
    key = os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')
    model_name = os.getenv('MODEL','')
    if not key or not model_name:
        raise ConfigurationError('Set MODEL and OPENROUTER_API_KEY (or OPENAI_API_KEY) in .env, then restart. Dataset preview and direct analytics work without an LLM key.')
    base_url = os.getenv('LLM_BASE_URL') or ('https://openrouter.ai/api/v1' if os.getenv('OPENROUTER_API_KEY') else 'https://api.openai.com/v1')
    async with asyncio.timeout(CHAT_TIMEOUT):
        tools = scoped_tools(await available_tools(), dataset_id)
        llm = ChatOpenAI(model=model_name, api_key=key, base_url=base_url, temperature=0,
                         timeout=60, max_retries=1)
        runner = create_agent(llm, tools, system_prompt=SYSTEM_PROMPT)
        messages = list(history or [])[-12:] + [{'role':'user','content':question}]
        result = await runner.ainvoke({'messages':messages}, config={'recursion_limit':24})
        final = result['messages'][-1]
        content = final.content
        if not isinstance(content,str):
            content = '\n'.join(b.get('text','') for b in content if isinstance(b,dict))
        traces = []
        for msg in result['messages']:
            if getattr(msg,'type','') == 'tool':
                raw = msg.content
                try: structured = json.loads(raw) if isinstance(raw,str) else raw
                except (ValueError,TypeError): structured = raw
                traces.append({'tool':msg.name, 'result': structured})
        return {'answer':content, 'tool_results':traces}
