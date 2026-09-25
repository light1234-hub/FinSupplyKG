from finsupplykg.config import PipelineConfig
from finsupplykg.financial_pipeline import (
    run_financial_pipeline,
)


def main() -> None:

    cfg = PipelineConfig()

    # Only one filing per form while testing
    cfg.filings_per_ticker = 1

    run_financial_pipeline(
        cfg
    )


if __name__ == "__main__":
    main()