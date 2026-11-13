"""Local semantic embeddings, loaded only when explicitly selected."""
from functools import lru_cache
from config.settings import EMBEDDING_MODEL
@lru_cache(maxsize=1)
def model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ValueError('Semantic RAG requires requirements-rag.txt. Install it or set RAG_BACKEND=tfidf.') from exc
    return SentenceTransformer(EMBEDDING_MODEL)
def encode(texts):
    return model().encode(texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False).astype('float32')
