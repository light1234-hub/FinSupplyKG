from finsupplykg.config import (
    DATA_DIR,
    PipelineConfig,
)

from finsupplykg.fetch import (
    fetch_filings,
)

from finsupplykg.financial_pipeline import (
    run_financial_pipeline,
)


def main() -> None:

    cfg = PipelineConfig()

    # Keep this small while testing the refactored pipeline.
    cfg.filings_per_ticker = 1

    print("=" * 60)
    print("FETCHING SEC FILINGS")
    print("=" * 60)

    filings = fetch_filings(
        cfg,
        DATA_DIR / "raw",
        cache_documents=False,
    )

    print()
    print(
        f"Fetched {len(filings)} filing records."
    )
    print()

    run_financial_pipeline(
        filings,
        cfg,
    )


if __name__ == "__main__":
    main()