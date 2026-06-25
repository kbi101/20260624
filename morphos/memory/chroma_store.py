"""ChromaDB-backed persistent memory store with Ollama embeddings."""

import os
from datetime import datetime

import chromadb

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "vector_store")


class ChromaStore:
    """Manages vector collections for facts and lessons using manual embeddings."""

    FACTS_COLLECTION = "facts"
    LESSONS_COLLECTION = "lessons"

    def __init__(self, embed_model="nomic-embed-text"):
        os.makedirs(DATA_DIR, exist_ok=True)
        self._client = chromadb.PersistentClient(path=DATA_DIR)
        self._embedder = OllamaEmbedder(embed_model)
        # Ensure both collections exist (ignore if they already do)
        for name in [self.FACTS_COLLECTION, self.LESSONS_COLLECTION]:
            try:
                self._client.get_collection(name=name)
            except Exception:
                self._client.create_collection(name=name)

    def _get_collection(self, name: str):
        return self._client.get_collection(name=name)

    def add_fact(self, text: str, session_id: str, confidence: float = 1.0):
        col = self._get_collection(self.FACTS_COLLECTION)
        uid = f"fact_{session_id}_{datetime.utcnow().isoformat()}_{abs(hash(text))}"
        embedding = self._embedder([text])[0]
        metadata = {
            "type": "fact",
            "session_id": session_id,
            "confidence": str(confidence),
            "timestamp": datetime.utcnow().isoformat(),
        }
        col.add(ids=[uid], documents=[text], embeddings=[embedding], metadatas=[metadata])

    def add_lesson(self, lesson: str, session_id: str):
        col = self._get_collection(self.LESSONS_COLLECTION)
        uid = f"lesson_{session_id}_{datetime.utcnow().isoformat()}_{abs(hash(lesson))}"
        embedding = self._embedder([lesson])[0]
        metadata = {
            "type": "lesson",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        col.add(ids=[uid], documents=[lesson], embeddings=[embedding], metadatas=[metadata])

    def query(self, text: str, n_results: int = 3, collection_names=None) -> list[dict]:
        if collection_names is None:
            collection_names = [self.FACTS_COLLECTION, self.LESSONS_COLLECTION]

        query_vec = self._embedder([text])[0]
        results = []

        for name in collection_names:
            col = self._get_collection(name)
            res = col.query(query_embeddings=[query_vec], n_results=n_results)
            if res and res.get("documents"):
                docs = res["documents"][0]
                metas = res.get("metadatas", [None])[0] or []
                dists = res.get("distances", [None])[0] or []
                for i, doc in enumerate(docs):
                    entry = {"text": doc, "source": name}
                    if i < len(metas):
                        entry["metadata"] = metas[i] or {}
                    if i < len(dists):
                        entry["distance"] = dists[i]
                    results.append(entry)

        results.sort(key=lambda x: x.get("distance", 999))
        return results[:n_results]

    def count(self, name=None):
        if name:
            col = self._get_collection(name)
            return {"collection": name, "count": col.count()}
        out = {}
        for n in [self.FACTS_COLLECTION, self.LESSONS_COLLECTION]:
            col = self._get_collection(n)
            out[n] = col.count()
        return out


class OllamaEmbedder:
    """Calls Ollama's embed API to produce vectors."""

    def __init__(self, model="nomic-embed-text"):
        import ollama
        self._ollama = ollama
        self._model = model

    def __call__(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        try:
            resp = self._ollama.embed(model=self._model, input=texts)
            vectors = resp.get("embeddings", [])
            if vectors:
                return vectors
        except Exception:
            pass
        # Fallback to zero vectors if Ollama is unavailable (graceful degradation)
        return [[0.0] * 768 for _ in texts]
