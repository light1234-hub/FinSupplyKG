import json
from pathlib import Path

from finsupplykg.chunk import chunk_section
from finsupplykg.config import PipelineConfig
from finsupplykg.normalize import normalize_text
from finsupplykg.parse import Section


def main():
    cfg = PipelineConfig()

    narrative_root = Path("data/processed/narratives")

    files = sorted(narrative_root.rglob("*.json"))

    if not files:
        raise FileNotFoundError(
            "No narrative JSON files found under data/processed/narratives"
        )

    path = files[0]

    with path.open("r", encoding="utf-8") as f:
        record = json.load(f)

    print(f"Testing: {path}")
    print(
        f"{record['ticker']} "
        f"{record['form']} "
        f"{record['accession']}"
    )

    total_chunks = 0

    for section_data in record.get("sections", []):
        cleaned_text = normalize_text(
            section_data.get("text", "")
        )

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

        total_chunks += len(chunks)

        print()
        print("=" * 70)
        print(f"Section: {section.section}")
        print(f"Method: {section.method}")
        print(f"Cleaned chars: {len(cleaned_text):,}")
        print(f"Chunks: {len(chunks)}")
        print("=" * 70)

        for chunk in chunks[:3]:
            print()
            print(f"Chunk ID: {chunk.chunk_id}")
            print(f"Index: {chunk.index}")
            print(f"Words: {len(chunk.raw_text.split())}")
            print()
            print(chunk.raw_text[:1500])
            print()

    print()
    print(f"Total chunks: {total_chunks}")


if __name__ == "__main__":
    main()