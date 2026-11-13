from fastmcp import FastMCP
from pandas_mcp import analytics
mcp = FastMCP('Pandas Analytics')
for function in (analytics.get_dataset_info, analytics.get_column_summary, analytics.aggregate_data,
                 analytics.groupby_data, analytics.filter_dataset, analytics.compare_dates):
    mcp.tool(function)
if __name__ == '__main__':
    mcp.run(transport='stdio', show_banner=False)
