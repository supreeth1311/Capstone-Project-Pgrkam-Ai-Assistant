# services/embeddings.py
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List

# multilingual, light-weight, great on CPU
_EMB_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(_EMB_MODEL_NAME)
    return _model

def embed_texts(texts: List[str]) -> np.ndarray:
    model = get_model()
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.array(vecs).astype("float32")

def embed_one(text: str) -> np.ndarray:
    return embed_texts([text])[0]
