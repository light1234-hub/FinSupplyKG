# FinSupplyKG — SEC preprocessing pipeline

FinSupplyKG preprocesses SEC filings for a 30-company AI and semiconductor
supply-chain universe. The pipeline fetches filings from SEC EDGAR, extracts
narrative sections and structured financial metrics, and saves the results as
JSON for downstream entity extraction, relation extraction, and Neo4j
ingestion.

## Current coverage

| Layer | Companies |
|---|---|
| Chip designers | `NVDA`, `AMD`, `INTC`, `AVGO`, `QCOM`, `TXN`, `NXPI`, `MU` |
| Chip equipment / design software | `AMAT`, `LRCX`, `KLAC`, `TER`, `SNPS`, `CDNS` |
| Storage | `WDC`, `STX` |
| Networking / components | `ANET`, `CSCO`, `APH`, `GLW` |
| Servers | `DELL`, `SMCI`, `HPE` |
| Big buyers | `MSFT`, `AMZN`, `GOOGL`, `META`, `ORCL`, `AAPL` |
| Automotive | `TSLA` |

All 30 companies currently use:

- `10-K` — annual report
- `10-Q` — quarterly report
- `8-K` — current / material-event report

Narrative extraction runs on `10-K`, `10-Q`, and `8-K`.

Structured financial extraction runs on `10-K` and `10-Q`.

The codebase still contains `20-F` and `6-K` support from earlier development,
but those forms are not part of the current 30-company regression scope.

## Setup

Run commands from the `preprocessing/` folder.

Create a virtual environment and install dependencies:

```bash
python -m venv ../.venv
../.venv/Scripts/python -m pip install -r requirements.txt
```

On macOS/Linux:

```bash
python3 -m venv ../.venv
../.venv/bin/pip install -r requirements.txt
```

Create your local environment file:

```bash
cp .env.example .env
```

Set your SEC identity in `.env` using the format required by SEC EDGAR:

```text
SEC_IDENTITY="Your Name your-email@example.com"
```

Do not commit `.env`. Only commit `.env.example` with placeholder values.

## Run the SEC preprocessing pipeline

```bash
python run_preprocessing.py
```

The runner:

1. creates `PipelineConfig`
2. fetches SEC filings once through `fetch_filings(...)`
3. caches HTML/text documents for narrative parsing
4. sends the same filing objects to the financial pipeline
5. sends the same filing objects to the narrative pipeline
6. saves processed JSON outputs

The current regression configuration uses:

```python
cfg.filings_per_ticker = 1
```

This means **one latest filing per ticker per form**, not one filing per year.

For example, with `filings_per_ticker = 1`, NVDA contributes:

```text
latest 10-K
latest 10-Q
latest 8-K
```

With `filings_per_ticker = 5`, the pipeline can fetch up to five filings of each form, so NVDA could contribute up to 15 filings.

## Pipeline

```text
                         SEC EDGAR
                             |
                             v
                      fetch_filings()
                             |
                FilingRecord + Filing object
                             |
                 +-----------+-----------+
                 |                       |
                 v                       v
        Narrative extraction     Financial extraction
                 |                       |
     +-----------+-----------+      filing.xbrl()
     |           |           |            |
  Datamule   EdgarTools   Regex       standardized
     |           |        slicer       statements
     +-----------+-----------+            |
                 |                   metric selection
          EX-99 exhibits                   |
          for 8-K / 6-K                 fallbacks
                 |                       |
          normalize_text()          fact metadata
                 |                       |
                 v                       v
         narrative JSON             financial JSON
                 |                       |
                 +-----------+-----------+
                             |
                             v
                 cleaning / normalization
                             |
                             v
                     entity extraction
                             |
                             v
                   relation extraction
                             |
                             v
                           Neo4j
```

## Narrative extraction

Narrative parsing is form-specific because SEC filings vary heavily in structure.

| Form | Primary strategy | Fallback(s) | Special handling |
|---|---|---|---|
| `10-K` | Datamule | EdgarTools → regex | Business, Risk Factors, MD&A |
| `10-Q` | EdgarTools | regex | Part-qualified Item matching |
| `8-K` | EdgarTools | regex | Extracts relevant Items + `EX-99` exhibits |
| `20-F` | regex | EdgarTools | Supports integrated annual-report headings |
| `6-K` | full filing text | — | Also extracts `EX-99` exhibits |

### Key narrative sections

`10-K`:

- Item 1 — Business
- Item 1A — Risk Factors
- Item 7 — Management's Discussion and Analysis

`10-Q`:

- Part I, Item 2 — Management's Discussion and Analysis
- Part II, Item 1A — Risk Factors

`8-K` includes supported current-report items such as results of operations, equity sales, management changes, Regulation FD, other events, and relevant `EX-99` exhibits.

`20-F` extracts canonical sections such as:

- key information / risk factors
- business
- operating and financial review

`6-K` stores the normalized full report and any `EX-99` exhibits.

## Structured financial extraction

Financial extraction runs only for:

```text
10-K
10-Q
20-F
```

The extractor uses filing-level XBRL and standardized EdgarTools statements first, then applies fallbacks when a metric is missing.

Canonical metrics:

- `revenue`
- `net_income`
- `cash`
- `assets`
- `inventory`
- `operating_income`
- `eps`

### Fallback hierarchy

For `10-K` and `10-Q`:

```text
standardized statements
        -> CompanyFacts
        -> filing-level raw XBRL
```

For `20-F`:

```text
standardized statements
        -> filing-level raw XBRL
```

The system does not assume that every `20-F` uses IFRS. It normalizes by financial meaning rather than by form name alone.

## Main modules

| Module | Responsibility |
|---|---|
| `finsupplykg/config.py` | tickers, form coverage, section specs, thresholds, date filters |
| `finsupplykg/fetch.py` | SEC EDGAR retrieval, filing metadata, HTML/text caching |
| `finsupplykg/parse.py` | form-specific narrative parser orchestration |
| `finsupplykg/regex_slicer.py` | heading detection and regex section boundaries |
| `finsupplykg/normalize.py` | conservative text normalization |
| `finsupplykg/narrative_pipeline.py` | narrative extraction and JSON persistence |
| `finsupplykg/xbrl.py` | standardized financial metric extraction and fallbacks |
| `finsupplykg/financial_pipeline.py` | structured financial JSON persistence |
| `run_preprocessing.py` | unified preprocessing entry point |

## Outputs

### Raw SEC cache

```text
data/raw/
```

Contains cached filing HTML, text, and metadata.

### Narrative JSON

```text
data/processed/narratives/{ticker}/{form}/{accession}.json
```

Example:

```json
{
  "ticker": "ASML",
  "form": "20-F",
  "accession": "...",
  "filing_date": "...",
  "sections": [
    {
      "section": "key_information",
      "method": "regex",
      "text": "..."
    },
    {
      "section": "business",
      "method": "regex",
      "text": "..."
    },
    {
      "section": "operating_review",
      "method": "regex",
      "text": "..."
    }
  ]
}
```

### Financial JSON

```text
data/processed/financials/{ticker}/{form}/{accession}.json
```

Example shape:

```json
{
  "ticker": "NVDA",
  "form": "10-K",
  "accession": "...",
  "filing_date": "...",
  "period_of_report": "...",
  "revenue": {"value": 0, "currency": "USD", "concept": "..."},
  "net_income": {"value": 0, "currency": "USD", "concept": "..."},
  "cash": {"value": 0, "currency": "USD", "concept": "..."},
  "assets": {"value": 0, "currency": "USD", "concept": "..."},
  "inventory": {"value": 0, "currency": "USD", "concept": "..."},
  "operating_income": {"value": 0, "currency": "USD", "concept": "..."},
  "eps": {"value": 0, "unit": "USD/shares", "concept": "..."},
  "missing_metrics": [],
  "status": "complete"
}
```

The numeric values above are placeholders to illustrate the schema.

## Current validation checkpoint

Latest one-filing-per-form regression:

```text
Narrative extraction
37 total filings
37 complete
0 empty
0 failed
87 sections extracted

Financial extraction
24 eligible filings
24 complete
0 partial
0 failed
```

This is a regression checkpoint for the current 13-company scope, not a guarantee of universal SEC filing coverage.

## Testing

Run the available tests from the `preprocessing/` folder:

```bash
python -m pytest tests
```

Useful focused tests include the narrative extraction and XBRL/financial extraction tests in the repository.

## Git / generated files

Do not commit runtime or local-secret files such as:

```text
.env
data/raw/
data/processed/
__pycache__/
.pytest_cache/
.venv/
venv/
*.log
```

Diagnostic scripts used during development can be kept under a separate `scripts/diagnostics/` directory if they are useful for future debugging.

## Next stage

The SEC extraction stage is complete for the current regression scope. The next stage is to clean and normalize the extracted narrative and financial outputs before running entity extraction, relation extraction, and Neo4j graph construction.
