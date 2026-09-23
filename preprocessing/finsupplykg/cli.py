"""FinSupplyKG preprocessing & indexing CLI.

    python -m finsupplykg.cli build [--tickers NVDA INTC] [--no-embed]
    python -m finsupplykg.cli search "TSMC CoWoS packaging capacity" [--ticker NVDA]
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import Counter
from dataclasses import asdict

from .config import DATA_DIR, PipelineConfig


def build(args: argparse.Namespace) -> None:
    from .chunk import chunk_section
    from .fetch import fetch_filings
    from .index import GeminiEmbedder, build_dense
    from .parse import extract_sections

    cfg = PipelineConfig()
    if args.tickers:
        cfg.tickers = [t.upper() for t in args.tickers]
    cfg.filings_per_ticker = args.filings_per_ticker
    cfg.max_words_per_chunk = args.max_words
    cfg.overlap_sentences = args.overlap

    index_dir = DATA_DIR / "index"
    sections_dir = DATA_DIR / "sections"
    index_dir.mkdir(parents=True, exist_ok=True)
    sections_dir.mkdir(parents=True, exist_ok=True)

    chunks, report = [], []
    for rec, filing in fetch_filings(cfg, DATA_DIR / "raw"):
        sections = extract_sections(rec, filing, cfg)
        (sections_dir / f"{rec.ticker}_{rec.accession.replace('-', '')}.json").write_text(
            json.dumps([asdict(s) for s in sections], indent=2))
        for sec in sections:
            sec_chunks = chunk_section(sec, cfg.max_words_per_chunk, cfg.overlap_sentences)
            chunks += sec_chunks
            report.append({"ticker": sec.ticker, "form": sec.form, "accession": sec.accession,
                           "filing_date": sec.filing_date, "section": sec.section, "method": sec.method,
                           "chars": len(sec.text), "chunks": len(sec_chunks)})

    if not chunks:
        raise SystemExit("No chunks produced; see warnings above.")

    with open(index_dir / "chunks.jsonl", "w") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c)) + "\n")
    with open(DATA_DIR / "parse_report.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(report[0]))
        w.writeheader()
        w.writerows(report)

    embedded = False
    if not args.no_embed:
        embedder = GeminiEmbedder(cfg.embedding_model, cfg.embedding_dim, cfg.embed_batch_size)
        build_dense([asdict(c) for c in chunks], embedder, index_dir)
        embedded = True
    else:
        (index_dir / "embeddings.npy").unlink(missing_ok=True)

    meta = {"n_chunks": len(chunks), "embedding_model": cfg.embedding_model if embedded else None,
            "embedding_dim": cfg.embedding_dim if embedded else None,
            "max_words_per_chunk": cfg.max_words_per_chunk, "overlap_sentences": cfg.overlap_sentences,
            "filing_window": [cfg.filing_start, cfg.filing_end]}
    (index_dir / "index_meta.json").write_text(json.dumps(meta, indent=2))

    print(f"\n{len(chunks)} chunks from {len({r['accession'] for r in report})} filings")
    print("parser used per section:", dict(Counter(r["method"] for r in report)))
    for t, n in sorted(Counter(c.ticker for c in chunks).items()):
        print(f"  {t:5s} {n}")
    print(f"index -> {index_dir}   report -> {DATA_DIR / 'parse_report.csv'}")


def search(args: argparse.Namespace) -> None:
    from .index import GeminiEmbedder, HybridIndex

    idx = HybridIndex(DATA_DIR / "index")
    embedder = None
    if idx.emb is not None and not args.bm25_only:
        embedder = GeminiEmbedder(idx.meta["embedding_model"], idx.meta["embedding_dim"])
    for score, c in idx.search(args.query, k=args.k, embedder=embedder,
                               ticker=args.ticker.upper() if args.ticker else None):
        print(f"\n[{score:.4f}] {c['ticker']} {c['form']} {c['filing_date']} {c['section']}#{c['index']}")
        print("   ", c["raw_text"][:400].replace("\n", " "), "...")


def main() -> None:
    p = argparse.ArgumentParser(prog="finsupplykg")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="fetch, parse, chunk and index filings")
    b.add_argument("--tickers", nargs="+")
    b.add_argument("--filings-per-ticker", type=int, default=1)
    b.add_argument("--max-words", type=int, default=PipelineConfig.max_words_per_chunk)
    b.add_argument("--overlap", type=int, default=PipelineConfig.overlap_sentences)
    b.add_argument("--no-embed", action="store_true", help="BM25 only; skip Gemini embeddings")
    b.set_defaults(func=build)

    s = sub.add_parser("search", help="hybrid BM25 + dense search over the built index")
    s.add_argument("query")
    s.add_argument("-k", type=int, default=5)
    s.add_argument("--ticker")
    s.add_argument("--bm25-only", action="store_true")
    s.set_defaults(func=search)

    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    # edgartools / datamule are chatty at INFO.
    for noisy in ("edgar", "httpx", "httpxthrottlecache", "datamule"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    args.func(args)


if __name__ == "__main__":
    main()
