import json
from pathlib import Path


def main():
    root = Path("data/cleaned/narratives")

    oversized = []
    tiny = []

    for path in sorted(root.rglob("*.json")):
        with path.open("r", encoding="utf-8") as f:
            record = json.load(f)

        for chunk in record.get("chunks", []):
            words = len(chunk.get("text", "").split())

            item = {
                "path": path,
                "ticker": chunk.get("ticker"),
                "form": chunk.get("form"),
                "section": chunk.get("section"),
                "chunk_id": chunk.get("chunk_id"),
                "words": words,
                "text": chunk.get("text", ""),
            }

            if words > 800:
                oversized.append(item)

            if words < 50:
                tiny.append(item)

    print("=" * 70)
    print("OVERSIZED CHUNKS")
    print("=" * 70)

    for chunk in oversized:
        print()
        print(
            f"{chunk['ticker']} "
            f"{chunk['form']} "
            f"{chunk['section']} "
            f"{chunk['chunk_id']} "
            f"({chunk['words']} words)"
        )
        print("-" * 70)
        print(chunk["text"][:2500])

    print()
    print("=" * 70)
    print("TINY CHUNKS (<50 WORDS)")
    print("=" * 70)

    for chunk in tiny:
        print()
        print(
            f"{chunk['ticker']} "
            f"{chunk['form']} "
            f"{chunk['section']} "
            f"{chunk['chunk_id']} "
            f"({chunk['words']} words)"
        )
        print("-" * 70)
        print(chunk["text"])


if __name__ == "__main__":
    main()