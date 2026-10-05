from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .config import DATA_DIR, PipelineConfig
from .parse import extract_sections


def save_narrative_sections(
    rec,
    sections,
    output_dir: Path,
) -> Path:
    """Save extracted narrative sections for one filing."""

    company_dir = (
        output_dir
        / rec.ticker
        / rec.form
    )

    company_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        company_dir
        / f"{rec.accession}.json"
    )

    payload = {
        "ticker": rec.ticker,
        "form": rec.form,
        "accession": rec.accession,
        "filing_date": rec.filing_date,
        "period_of_report": rec.period_of_report,
        "sections": [
            asdict(section)
            for section in sections
        ],
    }

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return path


def run_narrative_pipeline(
    filings: list[tuple[object, object]],
    cfg: PipelineConfig,
) -> dict:
    """Extract narrative sections from fetched SEC filings."""

    output_dir = (
        DATA_DIR
        / "processed"
        / "narratives"
    )

    total = 0
    complete = 0
    empty = 0
    failed = 0
    total_sections = 0

    for rec, filing in filings:

        total += 1

        try:
            sections = extract_sections(
                rec,
                filing,
                cfg,
            )

            if not sections:
                empty += 1

                print(
                    f"⚠ {rec.ticker:<5} "
                    f"{rec.form:<4} "
                    f"{rec.period_of_report} "
                    f"no sections extracted"
                )

                continue

            path = save_narrative_sections(
                rec,
                sections,
                output_dir,
            )

            complete += 1
            total_sections += len(sections)

            print(
                f"✓ {rec.ticker:<5} "
                f"{rec.form:<4} "
                f"{len(sections)} sections "
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
        "empty": empty,
        "failed": failed,
        "sections": total_sections,
    }

    print()
    print("=" * 60)
    print("NARRATIVE EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Total filings: {total}")
    print(f"Complete: {complete}")
    print(f"Empty: {empty}")
    print(f"Failed: {failed}")
    print(f"Sections extracted: {total_sections}")

    return summary