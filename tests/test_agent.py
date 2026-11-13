from langchain_core.tools import StructuredTool
from agent.ai_agent import scoped_tools
async def test_dataset_binding():
    async def call(dataset_id:str, query:str)->dict:
        """Test dataset binding."""
        return {'dataset_id':dataset_id,'query':query}
    tool=StructuredTool.from_function(coroutine=call)
    bound=scoped_tools([tool],'owned')[0]
    assert 'dataset_id' not in bound.args_schema['properties']
    assert (await bound.ainvoke({'query':'abc','dataset_id':'foreign'}))['dataset_id']=='owned'
