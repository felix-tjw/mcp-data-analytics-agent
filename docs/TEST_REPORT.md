# Validation report

Run date: 11 November 2026. Environment: Linux, Python 3.12.14. See requirements-lock-linux-py312.txt for the tested core dependency snapshot.

## Executed checks

- `python -m pytest -q`: **21 passed** in 15.76 seconds.
- `python -m pip check`: **No broken requirements found.**
- Python compilation and JavaScript syntax check: passed.
- `python scripts/smoke_test.py` against a running aggregator: passed; nine tools discovered, Titanic group statistics returned, three retrieval chunks returned.
- Original Titanic CSV and scoped synthetic Excel workbook: analyzed, with results in `observed_outputs.json`.

Tests cover null-aware calculations, exact totals versus pagination, null grouping, literal filters, invalid parameters, dates, duplicate headings, worksheets, project scope, index persistence, retrieval citations, missing credentials, upload errors, CSRF, session isolation and dataset binding.

The main integration test starts a real HTTP aggregator and local STDIO Pandas/RAG subprocesses. It verifies discovery/invocation through FastMCP and LangChain, then runs a two-tool conversation with a **scripted model**. It also performs a Flask file upload, activation, direct calculation and scripted chat through the same real MCP chain.

A separate test starts a fake search HTTP MCP server, aggregates all three backends, discovers ten tools and calls the namespaced search tool. This verifies the remote transport contract, not live Tavily authentication or search quality.

## Observed outputs

| Calculation | Result |
|---|---|
| Titanic passengers | 891 |
| Titanic survivors | 342 |
| First-class mean fare | 84.1546875 |
| Second-class mean fare | 20.6621831522 |
| Third-class mean fare | 13.6755501018 |
| Synthetic SilverBank tasks | 5, excluding the unrelated sixth row |
| Synthetic unassigned tasks | 1 |
| Synthetic total mandays | 15 |

## Remaining acceptance checks

- Real OpenRouter/OpenAI responses and Tavily search: credentials were not supplied. After configuration, run `python scripts/smoke_test.py --chat --web`; these flags can incur provider charges.
- Sentence Transformers model download and FAISS runtime: the optional heavyweight stack was not installed. Follow README section 8 and rerun the smoke test. TF-IDF tests do not establish semantic quality.
- Original RAG code and the real ProjectPlan.xlsx: not attached. A replacement server and explicitly synthetic workbook are supplied.
- Windows and legacy XLS: instructions/reader included; tests ran on Linux using CSV and XLSX.
- Browser visual/interaction testing: headless Chromium could not launch in this execution environment, and the separate browser could not reach its localhost server. No screenshot or visual-QA claim is made. Routes and the backend workflow were tested programmatically.

Non-failing dependency warnings concern Authlib's deprecated JOSE module and the LangChain adapter's older Streamable HTTP helper. Upgrade and retest dependencies together.

## Manual demonstration

1. Start `python scripts/start.py`, open port 5000 and confirm MCP connected.
2. Upload Titanic; test passenger count, fares by class and survivors over 50.
3. Upload ProjectPlan_SAMPLE.xlsx, choose DevPlan/header 3 and the documented project scope. Verify five tasks.
4. Ask for Debt Management context and its exact task count; inspect both evidence outputs.
5. Enable semantic RAG, then verify the reported backend and retrieval results.
6. Enable the remote provider and run the smoke test with chat/web flags. Verify external citations are distinct from calculated findings.
7. Repeat on the real workbook only after verifying project scope and task classifications.
