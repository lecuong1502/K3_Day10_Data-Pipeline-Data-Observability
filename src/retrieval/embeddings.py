from __future__ import annotations

from functools import lru_cache
import os

from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings

DEFAULT_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


@lru_cache(maxsize=4)
def _load_model(model_name: str, base_url: str) -> OllamaEmbeddings:
    return OllamaEmbeddings(model=model_name, base_url=base_url)


class MiniLMEmbeddings(Embeddings):
    """Local embeddings backend.

    Despite the legacy class name (kept unchanged so existing imports in
    retrieval/index.py keep working), this wraps a local embedding model
    served by Ollama (e.g. `bge-m3:567m`) instead of loading a
    sentence-transformers model with torch/CUDA.

    Requires `ollama serve` running and the model already pulled:
        ollama pull bge-m3:567m
    """

    def __init__(self, model_name: str, base_url: str | None = None):
        self.model_name = model_name
        self.base_url = base_url or DEFAULT_OLLAMA_BASE_URL
        self.model = _load_model(self.model_name, self.base_url)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.model.embed_query(text)