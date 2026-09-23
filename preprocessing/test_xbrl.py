from finsupplykg.config import PipelineConfig, DATA_DIR
from finsupplykg.fetch import fetch_filings
from finsupplykg.xbrl import (
    extract_metric_candidates,
    select_quarter_fact,
    REVENUE_TAGS,
)


cfg = PipelineConfig()

cfg.tickers = ["NVDA"]
cfg.filings_per_ticker = 1


filings = fetch_filings(
    cfg,
    DATA_DIR / "raw"
)


for rec, filing in filings:

    if rec.form != "10-Q":
        continue

    print("=" * 80)

    print("Ticker:", rec.ticker)
    print("Form:", rec.form)
    print("Accession:", rec.accession)
    print("Period:", rec.period_of_report)

    revenue_candidates = extract_metric_candidates(
        rec,
        cfg.sec_identity,
        REVENUE_TAGS
    )

    print(
        "\nRevenue candidates:",
        len(revenue_candidates)
    )

    for candidate in revenue_candidates:
        print("\n", candidate)

    quarter_revenue = select_quarter_fact(
        revenue_candidates,
        rec
    )

    print("\nSelected quarterly revenue:")
    print(quarter_revenue)