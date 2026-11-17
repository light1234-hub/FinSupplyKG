import json
import shutil
from collections import defaultdict
from pathlib import Path

from finsupplykg.chunk import chunk_section
from finsupplykg.config import PipelineConfig, forms_for
from finsupplykg.normalize import normalize_text
from finsupplykg.parse import Section


def select_latest_files(
    source_root: Path,
    cfg: PipelineConfig,
    filings_per_ticker: int,
) -> list[Path]:

    grouped = defaultdict(list)

    for path in source_root.rglob("*.json"):
        with path.open("r", encoding="utf-8") as f:
            record = json.load(f)

        ticker = record.get("ticker")
        form = record.get("form")
        filing_date = record.get("filing_date")

        if ticker not in cfg.tickers:
            continue

        if form not in forms_for(ticker):
            continue

        if not filing_date:
            continue

        grouped[(ticker, form)].append(
            (filing_date, path)
        )

    selected = []

    for _, records in grouped.items():
        records.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        selected.extend(
            path
            for _, path in records[:filings_per_ticker]
        )

    return sorted(selected)


def build_clean_chunks():
    cfg = PipelineConfig()

    filings_per_ticker = 1

    source_root = Path("data/processed/narratives")
    output_root = Path("data/cleaned/narratives")

    files = select_latest_files(
        source_root,
        cfg,
        filings_per_ticker,
    )

    if not files:
        raise FileNotFoundError(
            "No narrative files found under data/processed/narratives"
        )

    # Cleaned output is generated data, so rebuild it from scratch.
    if output_root.exists():
        shutil.rmtree(output_root)

    total_filings = 0
    total_sections = 0
    total_chunks = 0

    for path in files:
        with path.open("r", encoding="utf-8") as f:
            record = json.load(f)

        cleaned_chunks = []

        for section_data in record.get("sections", []):
            cleaned_text = normalize_text(
                section_data.get("text", "")
            )

            if not cleaned_text:
                continue

            section = Section(
                ticker=record["ticker"],
                form=record["form"],
                accession=record["accession"],
                filing_date=record["filing_date"],
                section=section_data["section"],
                method=section_data["method"],
                text=cleaned_text,
            )

            chunks = chunk_section(
                section,
                max_words=cfg.max_words_per_chunk,
                overlap=cfg.overlap_sentences,
            )

            total_sections += 1

            for chunk in chunks:
                cleaned_chunks.append(
                    {
                        "chunk_id": chunk.chunk_id,
                        "ticker": chunk.ticker,
                        "form": chunk.form,
                        "accession": chunk.accession,
                        "filing_date": chunk.filing_date,
                        "section": chunk.section,
                        "method": chunk.method,
                        "index": chunk.index,
                        "word_count": len(
                            chunk.raw_text.split()
                        ),
                        "text": chunk.raw_text,
                    }
                )

            total_chunks += len(chunks)

        output_record = {
            "ticker": record["ticker"],
            "form": record["form"],
            "accession": record["accession"],
            "filing_date": record["filing_date"],
            "chunk_count": len(cleaned_chunks),
            "chunks": cleaned_chunks,
        }

        relative = path.relative_to(source_root)
        output_path = output_root / relative

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                output_record,
                f,
                indent=2,
                ensure_ascii=False,
            )

        total_filings += 1

        print(
            f"✓ {record['ticker']:<5} "
            f"{record['form']:<4} "
            f"{len(cleaned_chunks):>3} chunks"
        )

    print()
    print("=" * 60)
    print("CLEAN CHUNK GENERATION COMPLETE")
    print("=" * 60)
    print(f"Filings:  {total_filings}")
    print(f"Sections: {total_sections}")
    print(f"Chunks:   {total_chunks}")


if __name__ == "__main__":
    build_clean_chunks()