"""Run against the aggregator. --chat/--web explicitly enable paid remote calls."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent.mcp_client import available_tools,call,health
from agent.ai_agent import answer
from config.settings import ROOT
from services.datasets import read_table,save_dataset

def validate_search_result(result):
    """MCP success can contain a provider-level quota/error response."""
    if not isinstance(result, dict):
        raise RuntimeError('Tavily returned an unexpected search response; no search success verified.')
    if result.get('code') or result.get('error'):
        detail = result.get('message') or result.get('error') or result['code']
        raise RuntimeError(f"Tavily search did not complete: {detail}")
    if not isinstance(result.get('results'), list):
        raise RuntimeError('Tavily returned no results array; no search success verified.')
    return result

async def main(args):
    print('Discovered:',', '.join(await health()))
    dataset=save_dataset(read_table(ROOT/'data/titanic.csv'),{'name':'titanic.csv'})['dataset_id']
    count=await call('pandas_aggregate_data',{'dataset_id':dataset,'function':'count'})
    assert count['value']==891,count
    grouped=await call('pandas_groupby_data',{'dataset_id':dataset,'group_by':['pclass'],'aggregations':{'fare':'mean'}})
    print(json.dumps(grouped,indent=2))
    retrieved=await call('rag_rag_search_dataset',{'dataset_id':dataset,'query':'First female passenger','top_k':3})
    print('Retrieved chunks:',len(retrieved['matches']))
    if args.web:
        tools=await available_tools()
        tool=next((t for t in tools if t.name.startswith('web_') and t.name.replace('-','_').endswith('tavily_search')),None)
        if tool is None:raise ValueError('Tavily search tool not found. Other providers can be tested through chat.')
        result = await call(tool.name, {'query':'Titanic passenger class historical context', 'max_results':3})
        print(json.dumps(validate_search_result(result), indent=2))
    if args.chat:
        q='Calculate average fare by passenger class and identify the highest using actual tool results.'
        if args.web:q+=' Then search for historical context and cite external sources separately.'
        print(json.dumps(await answer(q,dataset),indent=2))
    print('Smoke test passed.')
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--chat',action='store_true',help='Use the configured LLM; may incur charges.')
    parser.add_argument('--web',action='store_true',help='Call configured Tavily MCP; may incur charges.')
    asyncio.run(main(parser.parse_args()))
