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


def fetch_filings(cfg: PipelineConfig, raw_dir: Path) -> list[tuple[FilingRecord, object]]:
    """Download or reuse SEC filings for each configured ticker and form.

    If a filing date range is configured, only filings within that range
    are considered.
    """
    if not cfg.sec_identity:
        raise SystemExit("Set SEC_IDENTITY (e.g. 'Your Name you@example.com') in .env; EDGAR requires it.")
    set_identity(cfg.sec_identity)
    raw_dir.mkdir(parents=True, exist_ok=True)

    out = []
    for ticker in cfg.tickers:
        for form in forms_for(ticker):
            filings = Company(ticker).get_filings(
                form=form,
                amendments=False
            )

            if cfg.filing_start and cfg.filing_end:
                filings = filings.filter(
                    date=f"{cfg.filing_start}:{cfg.filing_end}"
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
            for filing in list(filings)[: cfg.filings_per_ticker]:
                slug = _slug(ticker, filing.accession_no)
                html_path, text_path, meta_path = (raw_dir / f"{slug}{ext}" for ext in (".htm", ".txt", ".json"))
                if meta_path.exists():
                    rec = FilingRecord(**json.loads(meta_path.read_text(encoding="utf-8")))
                else:
                    log.info("%s: downloading %s %s (%s)", ticker, form, filing.accession_no, filing.filing_date)
                    html_path.write_text(filing.html() or "", encoding="utf-8")
                    text_path.write_text(filing.text() or "", encoding="utf-8")
                    rec = FilingRecord(
                        ticker=ticker,
                        form=form,
                        accession=filing.accession_no,
                        filing_date=str(filing.filing_date),
                        period_of_report=str(getattr(filing, "period_of_report", "") or ""),
                        primary_document=str(getattr(filing, "primary_document", "") or f"{slug}.htm"),
                        html_path=str(html_path),
                        text_path=str(text_path),
                    )
                    meta_path.write_text(json.dumps(asdict(rec), indent=2))
                out.append((rec, filing))
    return out
