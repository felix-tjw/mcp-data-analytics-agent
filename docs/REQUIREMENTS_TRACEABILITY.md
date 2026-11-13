# Requirements traceability

Source: supplied MCP Data Analytics AI Agent Project Guide, 16 pages.

| Requirement | Implementation | Evidence / boundary |
|---|---|---|
| Pandas functions separate from MCP | analytics.py and pandas_server.py | Unit tests and real STDIO calls |
| Info, summary, aggregate, GroupBy, filters | Five core tools plus date comparison | Exact fixture and Titanic results |
| Validation and JSON safety | Whitelists, type checks, null normalization; no eval/query | Invalid-operation, null and empty-result tests |
| Remote Web Search MCP | HTTPS Streamable HTTP/SSE proxy with header authentication | Real HTTP fake-provider test; live Tavily needs credentials |
| Existing RAG reuse | Replacement server and RAG_SERVER_SCRIPT adapter contract | Original code was not attached; reuse is not verified |
| RAG index/search/info | rag_server.py and persistent vector_store.py | Real STDIO retrieval, index persistence and source citations tested |
| Semantic retrieval | Sentence Transformers and FAISS implementation | Optional stack not runtime-tested; default TF-IDF is lexical |
| One aggregator endpoint | FastMCP HTTP proxy over two local STDIO services | Nine local tools; ten including fake remote search |
| LangChain discovery and multi-tool execution | mcp_client.py and ai_agent.py | Real execution with a scripted model; live model requires credentials |
| Flask upload/chat/results | app.py, template, CSS, JavaScript | Full Flask -> agent -> HTTP -> STDIO pipeline tested |
| Session isolation | Bound dataset tool schemas and per-dataset indexes | Cross-session and identifier-override tests |
| Tables and evidence | Text-safe tables and JSON accordions | Syntax inspected; browser rendering unverified |
| CSV / Excel | CSV, XLS, XLSX; explicit sheet/header/project scope | CSV/XLSX tested; no XLS fixture supplied |
| Titanic exercises | Original public CSV included | 891 rows, 342 survivors, grouped fares recorded |
| SilverBank exercises | Synthetic workbook with two projects | Five scoped tasks; real workbook not attached |
| Configuration | .env.example, requirements, Linux lock, gitignore | Setup creates private .env; pip check passed |
| Documentation/evidence | README, tests, observed output JSON, test report | Included; no browser screenshots claimed |
