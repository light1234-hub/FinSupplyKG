import json
from collections import Counter
from pathlib import Path


def main():
    root = Path("data/cleaned/narratives")
    files = sorted(root.rglob("*.json"))

    total_chunks = 0
    empty_chunks = []
    oversized_chunks = []
    chunk_ids = []
    word_counts = []
    forms = Counter()
    tickers = Counter()
    sections = Counter()
    mismatched_counts = []

    for path in files:
        with path.open("r", encoding="utf-8") as f:
            record = json.load(f)

        chunks = record.get("chunks", [])

        forms[record["form"]] += 1
        tickers[record["ticker"]] += 1

        if record.get("chunk_count") != len(chunks):
            mismatched_counts.append(str(path))

        for chunk in chunks:
            total_chunks += 1

            chunk_id = chunk.get("chunk_id")
            text = chunk.get("text", "")
            word_count = len(text.split())

            chunk_ids.append(chunk_id)
            word_counts.append(word_count)
            sections[chunk.get("section")] += 1

            if not text.strip():
                empty_chunks.append(chunk_id)

            if word_count > 800:
                oversized_chunks.append(
                    (chunk_id, word_count)
                )

    duplicate_ids = [
        chunk_id
        for chunk_id, count
        in Counter(chunk_ids).items()
        if count > 1
    ]

    print("=" * 60)
    print("CLEAN CHUNK VALIDATION")
    print("=" * 60)

    print(f"Files:               {len(files)}")
    print(f"Chunks:              {total_chunks}")
    print(f"Unique chunk IDs:    {len(set(chunk_ids))}")
    print(f"Duplicate chunk IDs: {len(duplicate_ids)}")
    print(f"Empty chunks:        {len(empty_chunks)}")
    print(f"Count mismatches:    {len(mismatched_counts)}")

    if word_counts:
        print()
        print(f"Minimum words:       {min(word_counts)}")
        print(f"Maximum words:       {max(word_counts)}")
        print(
            f"Average words:       "
            f"{sum(word_counts) / len(word_counts):.1f}"
        )

    print(f"Chunks > 800 words:  {len(oversized_chunks)}")

    print()
    print("Filings by form:")
    for form, count in sorted(forms.items()):
        print(f"  {form:<5} {count}")

    print()
    print("Chunks by section:")
    for section, count in sections.most_common():
        print(f"  {section:<25} {count}")

    print()
    print("Filings by ticker:")
    for ticker, count in sorted(tickers.items()):
        print(f"  {ticker:<6} {count}")

    if oversized_chunks:
        print()
        print("Oversized chunks:")
        for chunk_id, words in oversized_chunks[:10]:
            print(f"  {chunk_id}: {words} words")


if __name__ == "__main__":
    main()