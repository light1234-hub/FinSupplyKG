# FinSupplyKG

## Status: In Development 

FinSupplyKG is a Python-based financial intelligence project exploring how public companies are connected through supply chains and how financial events may affect those relationships. The current focus is turning SEC filings into structured financial data and traceable text that can support later relationship extraction and knowledge-graph analysis.

## Current Features
* SEC filing retrieval: Retrieves filings from SEC EDGAR for a configured universe of 30 AI, semiconductor, and related companies. The current workflow covers 10-K, 10-Q, and 8-K filings, also includes 20-F and 6-K parsing support outside the current 30-company test scope.

* Narrative extraction: Identifies sections such as Business, Risk Factors, and Management's Discussion & Analysis (MD&A). Uses form-specific extraction strategies with Datamule, EdgarTools, and regex fallbacks to handle inconsistent filing formats.

* Extraction validation: Normalizes filing text and checks candidate section lengths and boundaries to reduce errors such as capturing a table-of-contents heading instead of the actual disclosure.

* Text preprocessing: Cleans extracted passages and divides them into sentence aware chunks, preserving identifiers, company tickers, filing dates, source sections, and other metadata for traceability.

* Financial data extraction: Uses XBRL to extract seven standardized metrics: revenue, net income, operating income, diluted EPS, cash, assets, and inventory. Reporting-period checks and fallback sources help resolve missing or inconsistent facts.

* Retrieval prototype: Includes BM25 search and optional embedding-based retrieval for the extracted text. This indexing workflow is separate from the main narrative and financial extraction runner.

## Technologies 
Python · SEC EDGAR · EdgarTools · Datamule · XBRL · pySBD · BM25 · optional Gemini embeddings

## How To Run
1.Navigate to the preprocessing directory:
   cd preprocessing
2. Create and activate a Python virtual environment.
3. Install dependencies: pip install -r requirements.txt.
4. Copy `.env.example` to `.env` and configure your SEC identity.
5. Run the narrative and financial extraction workflow:
   python run_preprocessing.py

## Next
Entity identification, company-relationship extraction, knowledge-graph construction (Neo4j), and analysis of financial-event propagation are planned stages, not completed capabilities in this repository. The frontend is currently a mock-data prototype, not a live prediction system.

## Documentation

For implementation details, setup instructions, and testing,
see the [Preprocessing Documentation](preprocessing/README.md).

For a detailed explanation of the extraction pipeline,
see the [Data Extraction Pipeline Report](docs/Data_Extraction_Pipeline.pdf).
