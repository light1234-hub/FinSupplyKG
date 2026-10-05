"""Locate and cache SEC filings from EDGAR."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from edgar import Company, set_identity

from .config import PipelineConfig, forms_for

log = logging.getLogger(__name__)


@dataclass
class FilingRecord:
    ticker: str
    form: str
    accession: str
    filing_date: str
    period_of_report: str
    primary_document: str
    html_path: str
    text_path: str


def _slug(ticker: str, accession: str) -> str:
    return f"{ticker}_{accession.replace('-', '')}"

def fetch_filings(
    cfg: PipelineConfig,
    raw_dir: Path,
    cache_documents: bool = True,
) -> list[tuple[FilingRecord, object]]:
    """Download or reuse SEC filings for each configured ticker and form."""

    if not cfg.sec_identity:
        raise SystemExit(
            "Set SEC_IDENTITY "
            "(e.g. 'Your Name you@example.com') "
            "in .env; EDGAR requires it."
        )

    set_identity(cfg.sec_identity)

    raw_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    out = []

    for ticker in cfg.tickers:

        for form in forms_for(ticker):

            filings = Company(
                ticker
            ).get_filings(
                form=form,
                amendments=False
            )

            if cfg.filing_start and cfg.filing_end:

                filings = filings.filter(
                    date=(
                        f"{cfg.filing_start}:"
                        f"{cfg.filing_end}"
                    )
                )

            if len(filings) == 0:

                if cfg.filing_start and cfg.filing_end:

                    log.warning(
                        "%s: no %s filed between %s and %s",
                        ticker,
                        form,
                        cfg.filing_start,
                        cfg.filing_end,
                    )

                else:

                    log.warning(
                        "%s: no %s filings found",
                        ticker,
                        form,
                    )

                continue

            for filing in list(
                filings
            )[:cfg.filings_per_ticker]:

                slug = _slug(
                    ticker,
                    filing.accession_no
                )

                html_path = (
                    raw_dir
                    / f"{slug}.htm"
                )

                text_path = (
                    raw_dir
                    / f"{slug}.txt"
                )

                meta_path = (
                    raw_dir
                    / f"{slug}.json"
                )

                # -----------------------------------------
                # LOAD OR CREATE METADATA
                # -----------------------------------------

                if meta_path.exists():

                    metadata = json.loads(
                        meta_path.read_text(
                            encoding="utf-8"
                        )
                    )

                    # Always use paths from the current project location.
                    metadata["html_path"] = str(
                        html_path
                    )

                    metadata["text_path"] = str(
                        text_path
                    )

                    rec = FilingRecord(
                        **metadata
                    )

                    # Repair the cached metadata file as well.
                    meta_path.write_text(
                        json.dumps(
                            asdict(rec),
                            indent=2
                        ),
                        encoding="utf-8",
                    )

                else:

                    log.info(
                        "%s: locating %s %s (%s)",
                        ticker,
                        form,
                        filing.accession_no,
                        filing.filing_date,
                    )

                    rec = FilingRecord(
                        ticker=ticker,
                        form=form,
                        accession=filing.accession_no,
                        filing_date=str(
                            filing.filing_date
                        ),
                        period_of_report=str(
                            getattr(
                                filing,
                                "period_of_report",
                                ""
                            ) or ""
                        ),
                        primary_document=str(
                            getattr(
                                filing,
                                "primary_document",
                                ""
                            ) or f"{slug}.htm"
                        ),
                        html_path=str(
                            html_path
                        ),
                        text_path=str(
                            text_path
                        ),
                    )

                    meta_path.write_text(
                        json.dumps(
                            asdict(rec),
                            indent=2
                        ),
                        encoding="utf-8",
                    )


                # -----------------------------------------
                # OPTIONAL HTML / TEXT CACHING
                # -----------------------------------------

                if cache_documents:

                    if not html_path.exists():

                        try:

                            html = (
                                filing.html()
                                or ""
                            )

                            if html:

                                html_path.write_text(
                                    html,
                                    encoding="utf-8"
                                )

                        except Exception as e:

                            log.warning(
                                "%s %s: "
                                "HTML unavailable: %s",
                                ticker,
                                form,
                                e,
                            )

                    if not text_path.exists():

                        try:

                            text = (
                                filing.text()
                                or ""
                            )

                        except Exception as e:

                            log.warning(
                                "%s %s: "
                                "filing.text() failed: %s",
                                ticker,
                                form,
                                e,
                            )

                            try:

                                text = (
                                    filing
                                    .full_text_submission()
                                    or ""
                                )

                            except Exception as fallback_error:

                                log.warning(
                                    "%s %s: "
                                    "full submission also "
                                    "failed: %s",
                                    ticker,
                                    form,
                                    fallback_error,
                                )

                                text = ""

                        if text:

                            text_path.write_text(
                                text,
                                encoding="utf-8"
                            )

                out.append(
                    (
                        rec,
                        filing
                    )
                )

    return out
