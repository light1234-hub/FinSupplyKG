"""Hybrid retrieval index: BM25 (sparse) + Gemini embeddings (dense)."""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

log = logging.getLogger(__name__)

_TOKEN = re.compile(r"[a-z0-9]+(?:[.\-'][a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class GeminiEmbedder:
    def __init__(self, model: str, dim: int, batch_size: int = 32):
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise SystemExit("Set GEMINI_API_KEY in .env (or run with --no-embed).")
        self.client = genai.Client(api_key=api_key)
        self.model, self.dim, self.batch_size = model, dim, batch_size

    def embed(self, texts: list[str], task_type: str) -> np.ndarray:
        from google.genai import types

        cfg = types.EmbedContentConfig(task_type=task_type, output_dimensionality=self.dim)
        out = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            for attempt in range(6):
                try:
                    resp = self.client.models.embed_content(model=self.model, contents=batch, config=cfg)
                    out += [e.values for e in resp.embeddings]
                    break
                except Exception as e:  # rate limits / transient 5xx
                    if attempt == 5:
                        raise
                    wait = 2 ** attempt * 5
                    log.warning("embed batch %d failed (%s); retrying in %ds", start, e, wait)
                    time.sleep(wait)
            log.info("embedded %d/%d", min(start + self.batch_size, len(texts)), len(texts))
        vecs = np.asarray(out, dtype=np.float32)
        # Truncated Gemini embeddings are not unit-norm; normalize so dot product = cosine.
        return vecs / np.clip(np.linalg.norm(vecs, axis=1, keepdims=True), 1e-12, None)


def build_dense(chunks: list[dict], embedder: GeminiEmbedder, out_dir: Path) -> np.ndarray:
    """Embed chunks, reusing cached vectors keyed by chunk_id so reruns only embed new chunks."""
    cache_path = out_dir / "embedding_cache.npz"
    cache: dict[str, np.ndarray] = {}
    if cache_path.exists():
        z = np.load(cache_path)
        if z["vecs"].shape[1] == embedder.dim:
            cache = dict(zip(z["ids"].tolist(), z["vecs"]))

    missing = [c for c in chunks if c["chunk_id"] not in cache]
    if missing:
        vecs = embedder.embed([c["text"] for c in missing], task_type="RETRIEVAL_DOCUMENT")
        cache.update(zip((c["chunk_id"] for c in missing), vecs))
        np.savez(cache_path, ids=np.array(list(cache)), vecs=np.stack(list(cache.values())))

    matrix = np.stack([cache[c["chunk_id"]] for c in chunks])
    np.save(out_dir / "embeddings.npy", matrix)
    return matrix


class HybridIndex:
    def __init__(self, index_dir: Path):
        self.chunks = [json.loads(l) for l in (index_dir / "chunks.jsonl").read_text().splitlines()]
        self.bm25 = BM25Okapi([tokenize(c["text"]) for c in self.chunks])
        emb = index_dir / "embeddings.npy"
        self.emb = np.load(emb) if emb.exists() else None
        self.meta = json.loads((index_dir / "index_meta.json").read_text())

    def search(self, query: str, k: int = 10, embedder: GeminiEmbedder | None = None,
               ticker: str | None = None, rrf_k: int = 60) -> list[tuple[float, dict]]:
        """Reciprocal-rank fusion of BM25 and dense rankings (dense only when embeddings exist)."""
        mask = np.array([ticker is None or c["ticker"] == ticker for c in self.chunks])
        rankings = [np.asarray(self.bm25.get_scores(tokenize(query)))]
        if self.emb is not None and embedder is not None:
            q = embedder.embed([query], task_type="RETRIEVAL_QUERY")[0]
            rankings.append(self.emb @ q)

        fused = np.zeros(len(self.chunks))
        for scores in rankings:
            scores = np.where(mask, scores, -np.inf)
            order = np.argsort(-scores)
            fused[order] += 1.0 / (rrf_k + np.arange(1, len(order) + 1))
        fused[~mask] = -np.inf
        top = np.argsort(-fused)[:k]
        return [(float(fused[i]), self.chunks[i]) for i in top]
