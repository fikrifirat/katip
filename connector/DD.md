# Katip DD: screen a name against Turkish public lists, from any AI app

Katip DD is part of the Katip Kalkan MCP server. One install gives the masking tools and five
due-diligence tools:

| Tool | What it does |
|---|---|
| `dd_screen` | Screens a person or company against MASAK asset-freeze lists (Law 6415 art. 5, 6, 7 and Law 7262), the ilan.gov.tr notices you looked up, and the Ticaret Sicili Gazetesi issues you added. Returns stored source records with the official link, score, band and the date of each source's data. Filters: birth year, ID number (exact match only, never echoed), lists, date range. |
| `dd_record` | One stored record in full, redacted the same way. |
| `dd_sources` | What each source holds, how fresh it is and its last failure. |
| `dd_update` | Fetches the four MASAK lists (about 10 requests, 2 s apart). |
| `dd_ilan_lookup` | Looks up ONE named target on ilan.gov.tr in a real browser on your computer (needs Playwright). |

Nothing is summarised: every hit is a record the source published. A "review" hit needs checking,
and no hit is not a clearance. Before a result reaches the AI, other people's ID numbers and
parents' names are removed; the listed name, dates, decision and links stay. A company's 10-digit tax
number (VKN) stays visible when it passes the VKN checksum and is labelled as one ("vergi no"):
it is not personal data and it pins the company down. Every 11-digit number (TCKN, YKN) is masked. In your own terminal
`katip-kalkan dd search NAME` shows the full record.

The index lives on your computer in `~/.katip/dd` (`KATIP_DD_HOME`). Fill it once:

```
katip-kalkan dd update                       # MASAK, about 10 requests
katip-kalkan dd add-gazette ~/Downloads/tsg  # Gazete PDFs you saved (add --ocr for scans)
katip-kalkan dd ilan-lookup "Firma Adı" --headed
```

Or ask the AI to call `dd_update`. Without `pip install`, the same commands run as
`python3 /ABS/PATH/katip/connector/server.py` for the server and
`PYTHONPATH=/ABS/PATH/katip/connector python3 -m katip_kalkan.cli dd ...` for the CLI.

## Install in each app

Replace `/ABS/PATH/katip` with where you cloned the repository. Every app starts the same local
server over stdio; nothing is hosted. **Tested** means a person or a script started it in that app
and called a DD tool; **config only** means the snippet follows the app's documented format but
nobody has run it yet.

| App | Status (21 Nov 2026) |
|---|---|
| Claude Code | **Tested**: connected, `dd_screen` called on a real MASAK snapshot, results redacted |
| Claude Desktop (.mcpb) | **Tested by script**: the built bundle lists 16 tools and answers `dd_sources` (`tests/smoke_mcpb.py`); not yet clicked through by a person |
| Cursor, VS Code, Windsurf, Codex, Gemini CLI | Config only |
| ChatGPT | Not deployed: needs the relay (below) |

**Claude Code** (plugin, includes DD): `claude plugin marketplace add fikrifirat/katip && claude plugin install katip-kalkan@katip`.
From a clone instead:

```
claude mcp add katip -- python3 /ABS/PATH/katip/connector/server.py
```

**Claude Desktop**: double-click `katip-kalkan.mcpb` from the latest Kalkan release.

**Cursor**: `~/.cursor/mcp.json` (or `.cursor/mcp.json` in a project)

```json
{"mcpServers": {"katip": {"command": "python3", "args": ["/ABS/PATH/katip/connector/server.py"]}}}
```

**VS Code** (Copilot agent mode): `.vscode/mcp.json`

```json
{"servers": {"katip": {"type": "stdio", "command": "python3", "args": ["/ABS/PATH/katip/connector/server.py"]}}}
```

**Windsurf**: `~/.codeium/windsurf/mcp_config.json`, same shape as Cursor.

**Codex CLI**: `~/.codex/config.toml`

```toml
[mcp_servers.katip]
command = "python3"
args = ["/ABS/PATH/katip/connector/server.py"]
```

**Gemini CLI**: `~/.gemini/settings.json`, same `mcpServers` shape as Cursor.

These apps send what the tools return to their own model provider. The masking tools exist for
that reason; DD results are already redacted as described above.

## ChatGPT

ChatGPT reaches only remote MCP servers, so it needs the relay (`katip-kalkan relay`,
[CHATGPT.md](CHATGPT.md)). With `KATIP_RELAY_DD=1` the relay adds `dd_screen` and `dd_sources`,
read-only and redacted. Callers cannot fetch: the operator refreshes the relay's index with the
CLI. It is off by default and **not deployed**.

Before anyone hosts it for other firms, KVKK has to be settled: the relay operator would hold
personal data (ID numbers, parents' names) and serve it for another firm's purpose. That needs a
basis under KVKK art. 5/2, a processing agreement, purpose and retention limits and a VERBİS
check. Not solved here.

## Why this is worth having, and where it is not

The fair test is: what does a lawyer get here that they could not get by asking Claude, or by
building it themselves with Claude in an afternoon? Each claim below has evidence or is marked
unproven.

**1. A chat assistant cannot read these sources.** Checked from our cloud machine on 21 Nov 2026:
the MASAK art. 5 page is a 5,095-byte app shell with no list rows in it (the data comes from a
JSON endpoint its own script calls); ilan.gov.tr's search API answers plain clients with HTTP 403;
www.ticaretsicil.gov.tr resets the connection. A web-browsing assistant sees an empty page or an
error, and may still answer. Katip fetches MASAK from the endpoint the site itself uses, runs
ilan.gov.tr in a real browser on the lawyer's own computer, and takes Gazette PDFs the lawyer
saved. It never forges headers or solves captchas.

**2. The answer is a record, not a sentence.** `dd_screen` returns the stored row, the official
link, the Resmî Gazete link and the date of the data. A language model asked "is X on the MASAK
list?" answers from memory or from a page it could not read. Here the model can only quote what
the tool returned.

**3. The matching is measured.** On a snapshot of 2,310 MASAK rows, held-out test split: 99.0%
of 1,545 name variants found at "review", 1.7% of 600 clean decoys flagged
(`lab/dd/results/eval.json`). Coverage checked against each list's own count (2,301 of 2,301) and
against the UN Security Council list (472 of 473 art. 5 entries found; the miss is listed under a
Turkish name). Turkish letters, legal forms, transliterations and word order are handled by rules
with tests (`lab/dd/test_dd.py`). The weak spot is also measured: one typo reaches "match" only
85.7% of the time.

**4. Freshness is shown, not assumed.** Every answer carries `data_as_of` per source and lists
the sources that are empty, so "no hit" can't silently mean "never loaded".

**5. Other people's data stays out of the model.** Lists and notices carry third parties' ID
numbers and parents' names. They are removed before the AI sees a result (tests in
`tests/test_dd_tools.py`).

**6. It runs in the lawyer's own tools.** One local server for Claude, Cursor, VS Code and
others, next to the masking tools the lawyer already uses.

What is **not** proven or not special:

- A technical person who knows the MASAK endpoint could fetch it in an afternoon. The value is in
  everything around it (the checks above), not in the fetch.
- We have not compared against commercial screening services (Dow Jones, LexisNexis, Refinitiv
  and Turkish providers). We don't know whether they cover MASAK art. 6/7 or ilan.gov.tr notices;
  that is unproven either way.
- No real lawyer queries yet. The matching numbers use generated variants; Uğur's past DD targets
  are the next labelled set.
- ilan.gov.tr works only one named target at a time on the lawyer's computer, and the Gazette only
  from PDFs the lawyer saves. Neither is a full index.
- Tested in Claude Code only; the other apps are config only (table above).
