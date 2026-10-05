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

from finsupplykg.narrative_pipeline import (
    run_narrative_pipeline,
)


def main() -> None:

    cfg = PipelineConfig()

    # One latest filing per ticker per form.
    # This gives the 37-filing regression scope.
    cfg.filings_per_ticker = 1

    print("=" * 60)
    print("FETCHING SEC FILINGS")
    print("=" * 60)

    filings = fetch_filings(
        cfg,
        DATA_DIR / "raw",
        cache_documents=True,
    )

    print()
    print(
        f"Fetched {len(filings)} filing records."
    )
    print()

    print("=" * 60)
    print("RUNNING FINANCIAL EXTRACTION")
    print("=" * 60)

    run_financial_pipeline(
        filings,
        cfg,
    )

    print()
    print("=" * 60)
    print("RUNNING NARRATIVE EXTRACTION")
    print("=" * 60)

    run_narrative_pipeline(
        filings,
        cfg,
    )


if __name__ == "__main__":
    main()