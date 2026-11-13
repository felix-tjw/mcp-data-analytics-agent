from fastmcp import FastMCP
from rag_mcp import vector_store
mcp = FastMCP('Dataset Retrieval')
@mcp.tool
def rag_load_dataset(dataset_id: str) -> dict:
    """Index an activated dataset. No arbitrary filesystem paths are accepted."""
    return vector_store.build(dataset_id)
@mcp.tool
def rag_search_dataset(dataset_id: str, query: str, top_k: int = 5, conditions: list[dict] | None = None) -> dict:
    """Retrieve source-labelled context. Use Pandas, never retrieved hit count, for totals. Optional AND filters scope retrieval."""
    return vector_store.search(dataset_id,query,top_k,conditions)
@mcp.tool
def rag_get_dataset_info(dataset_id: str) -> dict:
    """Report indexing status, retrieval backend and chunk count."""
    return vector_store.info(dataset_id)
if __name__ == '__main__': mcp.run(transport='stdio', show_banner=False)
