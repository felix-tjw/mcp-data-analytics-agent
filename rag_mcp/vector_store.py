import hashlib
import json
import shutil
import tempfile
import numpy as np
from config import settings
from services.datasets import load_dataset, metadata, dataset_dir, clean

def index_path(dataset_id):
    dataset_dir(dataset_id)  # validates ID before path use
    key = hashlib.sha256((settings.RAG_BACKEND + settings.EMBEDDING_MODEL).encode()).hexdigest()[:16]
    return settings.VECTOR_STORE_PATH / dataset_id / key

def build(dataset_id):
    target = index_path(dataset_id)
    if (target / 'manifest.json').exists(): return info(dataset_id)
    if settings.RAG_BACKEND not in {'tfidf', 'sentence-transformers'}:
        raise ValueError('RAG_BACKEND must be tfidf or sentence-transformers.')
    df = load_dataset(dataset_id); meta = metadata(dataset_id); docs = []
    for row_index, row in df.iterrows():
        text = '; '.join(f'{c}: {v}' for c,v in row.items() if v is not None and not (isinstance(v,float) and np.isnan(v)))
        # Preserve record identity for long rows; overlap is explicit.
        for start in range(0, max(len(text),1), 1000):
            docs.append({'text': text[start:start+1200], 'record': int(row_index)+1,
                         'source': meta['name'], 'sheet': meta.get('sheet'), 'chunk_offset': start})
        if len(docs)>20000: raise ValueError('RAG indexing supports at most 20,000 chunks. Activate a narrower project scope; Pandas still supports the full dataset.')
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = __import__('pathlib').Path(tempfile.mkdtemp(dir=target.parent))
    try:
        (tmp/'documents.json').write_text(json.dumps(docs,ensure_ascii=False),encoding='utf-8')
        if settings.RAG_BACKEND == 'sentence-transformers':
            from rag_mcp.embeddings import encode
            np.save(tmp/'vectors.npy', encode([d['text'] for d in docs]), allow_pickle=False)
        manifest = {'dataset_id': dataset_id, 'chunks': len(docs), 'rows': len(df),
                    'backend': settings.RAG_BACKEND,
                    'retrieval': 'semantic' if settings.RAG_BACKEND == 'sentence-transformers' else 'lexical TF-IDF',
                    'embedding_model': settings.EMBEDDING_MODEL if settings.RAG_BACKEND == 'sentence-transformers' else None}
        (tmp/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        try: tmp.rename(target)
        except OSError:
            if not (target/'manifest.json').exists(): raise
    finally:
        if tmp.exists(): shutil.rmtree(tmp)
    return info(dataset_id)

def info(dataset_id):
    target = index_path(dataset_id)
    if not (target/'manifest.json').exists():
        return {'indexed': False, 'backend': settings.RAG_BACKEND}
    return {'indexed': True, **json.loads((target/'manifest.json').read_text(encoding='utf-8'))}

def search(dataset_id, query, top_k=5, conditions=None):
    if not query.strip(): raise ValueError('Search query cannot be empty.')
    if not 1 <= top_k <= 20: raise ValueError('top_k must be 1-20.')
    build(dataset_id); target = index_path(dataset_id)
    docs = json.loads((target/'documents.json').read_text(encoding='utf-8'))
    indices = list(range(len(docs)))
    if conditions:
        from pandas_mcp.analytics import filtered
        rows = set(filtered(load_dataset(dataset_id), conditions).index + 1)
        indices = [i for i,d in enumerate(docs) if d['record'] in rows]
    if not indices: return {'matches': [], 'backend': settings.RAG_BACKEND}
    if settings.RAG_BACKEND == 'sentence-transformers':
        from rag_mcp.embeddings import encode
        import faiss
        vectors = np.load(target/'vectors.npy',allow_pickle=False)[indices]
        index = faiss.IndexFlatIP(vectors.shape[1]); index.add(vectors)
        scores, positions = index.search(encode([query]), min(top_k,len(indices)))
        ranked = [(indices[int(p)],float(s)) for p,s in zip(positions[0],scores[0]) if p >= 0]
    else:
        from sklearn.feature_extraction.text import TfidfVectorizer
        vectorizer = TfidfVectorizer(ngram_range=(1,2),max_features=50000,sublinear_tf=True)
        try:
            matrix = vectorizer.fit_transform([docs[i]['text'] for i in indices])
            scores = (matrix @ vectorizer.transform([query]).T).toarray().ravel()
            ranked = [(indices[int(p)],float(scores[p])) for p in np.argsort(-scores)[:top_k]]
        except ValueError:
            ranked = []
    return clean({'matches': [{**docs[i], 'score': score} for i,score in ranked if score > 0],
                  'backend': settings.RAG_BACKEND,
                  'note': 'Retrieved chunks are contextual evidence, not a complete result set for counting.'})
