from pathlib import Path
import os
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
def path(name, default):
    p = Path(os.getenv(name, default)).expanduser()
    return p if p.is_absolute() else ROOT / p
UPLOAD_FOLDER = path('UPLOAD_FOLDER', 'uploads')
VECTOR_STORE_PATH = path('VECTOR_STORE_PATH', 'vector_store')
AGGREGATOR_HOST = os.getenv('AGGREGATOR_HOST', '127.0.0.1')
AGGREGATOR_PORT = int(os.getenv('AGGREGATOR_PORT', '8000'))
AGGREGATOR_URL = os.getenv('AGGREGATOR_URL', f'http://{AGGREGATOR_HOST}:{AGGREGATOR_PORT}/mcp')
MAX_ROWS = 100_000
MAX_COLUMNS = 200
MAX_UPLOAD_MB = int(os.getenv('MAX_UPLOAD_MB', '20'))
TOOL_TIMEOUT = float(os.getenv('TOOL_TIMEOUT', '90'))
CHAT_TIMEOUT = float(os.getenv('CHAT_TIMEOUT', '180'))
RAG_BACKEND = os.getenv('RAG_BACKEND', 'tfidf')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
