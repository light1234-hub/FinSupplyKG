from finsupplykg.config import PipelineConfig, DATA_DIR
from finsupplykg.fetch import fetch_filings
from finsupplykg.xbrl import extract_financial_record


cfg = PipelineConfig()

cfg.tickers = ["AVGO"]
cfg.filings_per_ticker = 1


filings = fetch_filings(
    cfg,
    DATA_DIR / "raw"
)


for rec, filing in filings:

    if rec.form != "10-Q":
        continue

    record = extract_financial_record(
        rec,
        cfg.sec_identity
    )

    print("\n" + "=" * 80)
    print(record)