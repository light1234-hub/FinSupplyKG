from __future__ import annotations

import json

from pathlib import Path

from .config import DATA_DIR, PipelineConfig
from .fetch import fetch_filings
from .xbrl import extract_financial_record


STRUCTURED_FORMS = {
    "10-K",
    "10-Q",
    "20-F",
}


def save_financial_record(
    record: dict,
    output_dir: Path
) -> Path:
    """Save one normalized financial record as JSON."""

    ticker = record["ticker"]
    form = record["form"]
    accession = record["accession"]

    company_dir = (
        output_dir
        / ticker
        / form
    )

    company_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    path = (
        company_dir
        / f"{accession}.json"
    )

    path.write_text(
        json.dumps(
            record,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    return path


def run_financial_pipeline(
    cfg: PipelineConfig | None = None
) -> dict:
    """Fetch filings, extract structured financials and save them."""

    if cfg is None:
        cfg = PipelineConfig()

    raw_dir = DATA_DIR / "raw"

    output_dir = (
        DATA_DIR
        / "processed"
        / "financials"
    )

    filings = fetch_filings(
        cfg,
        raw_dir,
        cache_documents=False,
    )

    total = 0
    complete = 0
    partial = 0
    failed = 0

    for rec, filing in filings:

        if rec.form not in STRUCTURED_FORMS:
            continue

        total += 1

        try:

            record = extract_financial_record(
                rec,
                filing,
                cfg.sec_identity
            )

            path = save_financial_record(
                record,
                output_dir
            )

            if record["status"] == "complete":

                complete += 1

                print(
                    f"✓ {rec.ticker:<5} "
                    f"{rec.form:<4} "
                    f"{rec.period_of_report} "
                    f"-> {path}"
                )

            else:

                partial += 1

                print(
                    f"⚠ {rec.ticker:<5} "
                    f"{rec.form:<4} "
                    f"missing="
                    f"{record['missing_metrics']} "
                    f"-> {path}"
                )

        except Exception as exc:

            failed += 1

            print(
                f"✗ {rec.ticker:<5} "
                f"{rec.form:<4} "
                f"{rec.period_of_report} "
                f"ERROR: {exc}"
            )

    summary = {
        "total": total,
        "complete": complete,
        "partial": partial,
        "failed": failed,
    }

    print("\n" + "=" * 60)
    print("FINANCIAL EXTRACTION COMPLETE")
    print("=" * 60)

    print(
        f"Total records: {total}"
    )

    print(
        f"Complete: {complete}"
    )

    print(
        f"Partial: {partial}"
    )

    print(
        f"Failed: {failed}"
    )

    return summary