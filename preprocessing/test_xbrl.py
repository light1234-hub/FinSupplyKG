from finsupplykg.config import PipelineConfig, DATA_DIR
from finsupplykg.fetch import fetch_filings
from finsupplykg.xbrl import extract_financial_record


cfg = PipelineConfig()

cfg.tickers = [
    "NVDA",
    "INTC",
    "AMD",
    "AVGO",
    "QCOM",
    "TXN",
    "MU",
    "AMAT",
    "LRCX",
    "MRVL",
    "WDC",
    "TSM",
    "ASML",
]

cfg.filings_per_ticker = 1


filings = fetch_filings(
    cfg,
    DATA_DIR / "raw"
)


total = 0
complete = 0
partial = 0


for rec, filing in filings:

    if rec.form not in {
        "10-K",
        "10-Q",
        "20-F",
    }:
        continue

    total += 1

    try:
        record = extract_financial_record(
            rec,
            filing,
            cfg.sec_identity
        )

        if record["status"] == "complete":

            complete += 1

            print(
                f"✓ {rec.ticker:<5} "
                f"{rec.form:<4} "
                f"{rec.period_of_report}"
            )

        else:

            partial += 1

            print(
                f"⚠ {rec.ticker:<5} "
                f"{rec.form:<4} "
                f"missing={record['missing_metrics']}"
            )

    except Exception as exc:

        partial += 1

        print(
            f"✗ {rec.ticker:<5} "
            f"{rec.form:<4} "
            f"ERROR: {exc}"
        )


print("\n" + "=" * 60)

print("Total records:", total)
print("Complete:", complete)
print("Partial / failed:", partial)