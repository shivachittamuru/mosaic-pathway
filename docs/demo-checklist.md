# Demo Checklist

A practical, ordered checklist for demonstrating the Mosaic Family Pathway MVP on a
clean machine. Every command is copy-pasteable PowerShell and matches the current
project. Work through the sections in order the first time; later demos can start at
step 6 once the local index exists.

Allow extra time before the first demo. The initial embedding-model download and the
knowledge-base build both take several minutes.

## 1. Prerequisites

* [ ] Windows with PowerShell, or an equivalent shell with the commands adjusted
* [ ] Git installed and configured
* [ ] `uv` installed
* [ ] An Anthropic account with API access
* [ ] An Anthropic API key created in the Anthropic Console
* [ ] A Claude model that supports structured outputs, such as a Claude 4.5 or later model
* [ ] The private Mosaic PDF and DOCX files, received separately and never committed
* [ ] Network access for the first embedding-model download and for every generation call

Confirm the tools:

```powershell
git --version
uv --version
```

## 2. Environment setup

Clone and install:

```powershell
git clone https://github.com/shivachittamuru/mosaic-pathway.git
cd mosaic-pathway
uv sync
```

Confirm the interpreter:

```powershell
uv run python --version
```

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set your own API key and model. Do not paste real values into chat,
tickets, or slides:

```dotenv
ANTHROPIC_API_KEY=YOUR-ANTHROPIC-API-KEY
ANTHROPIC_MODEL=YOUR-CLAUDE-MODEL
ANTHROPIC_MAX_TOKENS=
MOSAIC_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

`ANTHROPIC_MAX_TOKENS` is optional. Leave it blank to use the project default.

No sign-in command is needed. The key in `.env` is the only credential, it is read by
the settings model, and `.env` is ignored by Git.

## 3. Private source placement

* [ ] Copy the supplied Mosaic PDF and DOCX files into `data/raw/`
* [ ] Confirm each filename matches the `filename` field in `data/inventory/sources.json`
* [ ] Confirm Git ignores them

```powershell
Get-ChildItem data\raw | Select-Object Name
git status --short
```

`git status --short` must not list anything under `data/raw/`. A missing or misnamed file
causes the next step to fail with a clear `FileNotFoundError` naming the source ID.

## 4. Knowledge-base build

```powershell
uv run python -m mosaic_pathway.knowledge_base
```

Expected output: nine documents processed, 807 records generated, and a per-source
count. The records are written to `data/processed/source_records.json`, which stays out
of Git. Only counts are printed, never source text.

## 5. Vector-index build

```powershell
uv run python -m mosaic_pathway.vector_store
```

Expected output: the model name, dimension 384, 807 records indexed, the collection name
`mosaic_sources`, and the local database path. The first run downloads
`all-MiniLM-L6-v2` before indexing begins.

This command rebuilds the collection from scratch. Rerun it whenever the knowledge base
changes.

## 6. Offline checks

Run all four gates. None of them contacts the Anthropic API, Qdrant, or the network:

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Expected: 189 tests passing, no lint findings, all files formatted, and no type errors.
The full suite takes a few minutes because it imports the embedding stack.

## 7. Retrieval demo

Show that semantic search over local Mosaic content works before involving any model:

```powershell
uv run python -m mosaic_pathway.slice2b_demo
```

Three synthetic family queries print their top five matches with similarity scores,
record IDs, titles, and truncated previews. Point out that a single source cannot occupy
every slot, which is the per-source cap at work.

Then show the retrieval baseline:

```powershell
uv run python -m mosaic_pathway.retrieval_evaluation
```

Expected: 10 queries, 8 hits at five, a hit rate of 0.80, the mean reciprocal rank over
the hits, and the two named misses.

## 8. End-to-end generation demo

```powershell
uv run python -m mosaic_pathway.slice3_demo
```

This runs the complete workflow for the synthetic family in
`examples/family_nature.json`: query construction, retrieval, Claude generation,
and citation verification. The grounded result is written to
`data/manual/grounded_pathway_output.json`, which is ignored by Git.

The generated pathway prints to the terminal. It contains real Mosaic-derived content,
so treat the terminal as private during screen sharing.

`slice1_demo` demonstrates the earlier manual-context approach and requires a
hand-curated `data/manual/context.json`. Skip it unless you have that file.

## 9. Evaluation demo

```powershell
uv run python -m mosaic_pathway.slice4_evaluation
```

Six synthetic cases run end to end, so this takes noticeably longer than a single
generation and makes six Anthropic API calls. Expected output is one line per case, then
6 of 6 cases passed and 60 of 60 checks passed.

Only outcomes print. The grounded results themselves go to `data/evaluation/`, which is
ignored by Git.

For the human side of evaluation, open [pathway-review-rubric.md](pathway-review-rubric.md)
and `examples/human_review_template.csv`.

## 10. Streamlit demo

Stop every other command first. See section 14.

```powershell
uv run streamlit run src/mosaic_pathway/app.py
```

The browser opens at `http://localhost:8501`. The first load takes 30 to 60 seconds
while the embedding stack imports, and the page may look empty until it finishes.

A good demo path:

1. Fill in one learner, or tick the second-learner box to show two.
2. Submit, and narrate the spinner text while retrieval and generation run.
3. Read the generated pathway in the right column.
4. Open "How this pathway was created" to explain the four steps.
5. Decide in advance whether to open "Sources used", which reveals previews of real
   Mosaic passages.
6. Use "Clear pathway" to return to the placeholder without rebuilding anything.

Stop the app with Ctrl+C when finished.

## 11. FastAPI demo

Stop the Streamlit app first. Both processes cannot hold the vector store at once.

```powershell
uv run uvicorn mosaic_pathway.api:app --reload
```

In a second terminal, check that the process is alive:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/health
```

Generate a pathway from the synthetic family file:

```powershell
$intake = Get-Content examples\family_nature.json -Raw
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/pathways -Method Post -ContentType "application/json" -Body $intake | ConvertTo-Json -Depth 8
```

Open `http://127.0.0.1:8000/docs` to show the generated interface and the `FamilyIntake`
schema. Point out that the `sources` array carries previews capped at 250 characters
rather than complete passages, and that the access log records request lines only.

Stop the server with Ctrl+C when finished.

## 12. Privacy checks before screen sharing

Run through this list before anyone else sees your screen:

* [ ] Close `.env` and any editor tab showing your Anthropic API key
* [ ] Close editor tabs for anything under `data/raw/`, `data/processed/`,
  `data/manual/`, or `data/evaluation/`
* [ ] Clear the terminal scrollback so earlier output and any credential fragment is gone
* [ ] Confirm nothing private is staged or untracked

```powershell
git status --short
```

* [ ] Spot-check the ignore rules

```powershell
git check-ignore -v .env data\raw\example.pdf data\processed\source_records.json data\evaluation\report.json
```

Each path must report a matching rule. A path that reports nothing is not ignored.

* [ ] Decide in advance whether to open the Streamlit "Sources used" expander, which
  shows previews of real Mosaic text
* [ ] Remember that `slice3_demo` prints a full generated pathway to the terminal
* [ ] Silence notifications so unrelated messages do not appear mid-demo

## 13. Expected limitations and troubleshooting

State these limitations before questions arrive rather than after:

* Retrieval hits an expected source for 8 of 10 synthetic queries, not 10 of 10.
* Roughly 82 percent of records come from the website export, so the per-source cap is
  doing real work.
* The deterministic checks confirm structure and citation validity. They do not prove
  that a cited passage supports the claim made about it.
* The personalization checks are lexical, so they reward a repeated keyword.
* The API has no authentication and is for local development only.
* Generation is synchronous, so the interface waits for the whole model call.

Common failures:

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValidationError` mentioning `ANTHROPIC_API_KEY` or `ANTHROPIC_MODEL` | `.env` missing or incomplete | Copy `.env.example` to `.env` and fill both values |
| Message that collection `mosaic_sources` was not found | The index was never built | Run `uv run python -m mosaic_pathway.vector_store` |
| Storage or lock error mentioning `data/vector_store` | Another process still owns the database | Stop the other process. See section 14 |
| API returns 503 `anthropic_authentication_failed`, or the UI mentions `ANTHROPIC_API_KEY` | The key is missing, revoked, or lacks access to the model | Create a new key in the Anthropic Console and update `.env` |
| API returns 503 `anthropic_rate_limited` | The account hit an Anthropic rate limit | Wait, then rerun. Avoid the six-case evaluation back to back |
| API returns 503 `anthropic_unreachable` | Network failure or request timeout | Check connectivity, then rerun |
| `FileNotFoundError` naming a source ID | A raw file is missing or misnamed | Match the filename in `data/inventory/sources.json` exactly |
| API returns 503 `service_unavailable` while `/health` returns ok | Startup failed but the process stayed up | Read the message in the response, fix the cause, restart uvicorn |
| API returns 502 `pathway_not_grounded` | The model cited a passage that was not retrieved | Rerun. Persistent failures belong in the evaluation, not the demo |
| Streamlit shows a blank page for a minute | Sentence-transformers is still importing | Wait for the first load to finish |

## 14. Shutdown guidance

The local Qdrant database takes an exclusive file lock on `data/vector_store/`. Exactly
one process may own it at a time, which means the Streamlit app, the API, and every
command-line demo are mutually exclusive.

Before starting any of them:

* [ ] Press Ctrl+C in the terminal running Streamlit or uvicorn and wait for the prompt
  to return
* [ ] Confirm no leftover interpreter is still running

```powershell
Get-Process -Name python, streamlit -ErrorAction SilentlyContinue | Select-Object Id, ProcessName
```

* [ ] Stop any stray process from the demo by its own process ID, after confirming it is
  not something you need

A demo that switches between the Streamlit app and the API should stop the first one
completely before starting the second. Closing only the browser tab is not enough,
because the server process keeps the lock.
