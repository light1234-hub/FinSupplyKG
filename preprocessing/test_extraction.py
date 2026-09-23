from finsupplykg.config import PipelineConfig, DATA_DIR
from finsupplykg.fetch import fetch_filings
from finsupplykg.parse import extract_sections


cfg = PipelineConfig()

# Test only one company first
cfg.tickers = ["TSM"]

# Latest 1 of each form:
# 1 x 10-K
# 1 x 10-Q
# 1 x 8-K
cfg.filings_per_ticker = 1


for rec, filing in fetch_filings(
    cfg,
    DATA_DIR / "raw"
):
    print("\n" + "=" * 80)
    print("Ticker:", rec.ticker)
    print("Form:", rec.form)
    print("Accession:", rec.accession)
    print("Filing date:", rec.filing_date)

    sections = extract_sections(
        rec,
        filing,
        cfg
    )

    print("Sections found:", len(sections))

    for section in sections:
        print(
            f"\n[{section.section}] "
            f"method={section.method} "
            f"chars={len(section.text)}"
        )

        print(section.text[:500])
        print("...")