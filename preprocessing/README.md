# FinSupplyKG — preprocessing & indexing

Fetches 10-K / 20-F filings for 13 semiconductor companies, extracts the supply-chain-relevant
sections, chunks them with pySBD, and builds a hybrid BM25 + Gemini dense index.

## Setup

All commands run from this `preprocessing/` folder; the virtualenv lives at the repo root.

```bash
cd preprocessing
python3 -m venv ../.venv && ../.venv/bin/pip install -r requirements.txt
cp .env.example .env   # set SEC_IDENTITY and GEMINI_API_KEY
```

## Run

```bash
../.venv/bin/python -m finsupplykg.cli build                 # all 13 tickers, with embeddings
../.venv/bin/python -m finsupplykg.cli build --no-embed      # BM25 only (no API key needed)
../.venv/bin/python -m finsupplykg.cli build --tickers NVDA TSM --max-words 800 --overlap 7
../.venv/bin/python -m finsupplykg.cli search "reliance on TSMC CoWoS capacity" --ticker NVDA
../.venv/bin/python -m pytest tests
```

## Pipeline

| Stage | Module | Notes |
|---|---|---|
| Fetch | `fetch.py` | edgartools; original filings only (no 10-K/A); filing window 2024-01-01 → 2025-12-31, latest per ticker |
| Parse 10-K | `parse.py` | datamule (AST, iXBRL) → edgartools accessors → regex slicer |
| Parse 20-F | `parse.py` | regex slicer → edgartools accessors |
| Normalize | `normalize.py` | NFKC, zero-width chars, non-breaking hyphens, repeated layout lines |
| Chunk | `chunk.py` | pySBD sentences, word-budgeted windows with 7-sentence overlap, `[TICKER]` prefix |
| Index | `index.py` | BM25Okapi + `models/gemini-embedding-2` (3,072-d, `RETRIEVAL_DOCUMENT`), RRF fusion at query time |

Sections: 10-K Items 1, 1A, 7; 20-F Items 3, 4, 5. A parser result is accepted only if it is
between 5k and 250k chars, otherwise the next parser is tried.

## Outputs (`data/`)

- `raw/` cached filing HTML/text + metadata
- `sections/` extracted sections per filing, with the parser that produced each
- `parse_report.csv` per-section parser, size and chunk count
- `index/chunks.jsonl`, `index/embeddings.npy`, `index/index_meta.json`
