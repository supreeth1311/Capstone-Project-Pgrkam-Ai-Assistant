# services/rag.py
import faiss
import numpy as np
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader
from services.embeddings import embed_texts, embed_one

class VectorStore:
    def __init__(self):
        self.index = None
        self.chunks: List[str] = []
        self.metas: List[Dict[str, Any]] = []
        self.dim = None

    def build(self, texts: List[str], metas: List[Dict[str, Any]]):
        self.chunks = texts
        self.metas = metas
        embs = embed_texts(texts)
        self.dim = embs.shape[1]
        self.index = faiss.IndexFlatIP(self.dim)  # dot-product since normalized
        self.index.add(embs)

    def search(self, query: str, k: int = 5) -> List[Tuple[str, Dict[str, Any], float]]:
        if not self.index:
            return []
        q = embed_one(query).reshape(1, -1)
        scores, ids = self.index.search(q, k)
        out = []
        for score, idx in zip(scores[0], ids[0]):
            if idx == -1:
                continue
            out.append((self.chunks[idx], self.metas[idx], float(score)))
        return out

def pdf_to_chunks(file, max_chars: int = 900, overlap: int = 150):
    reader = PdfReader(file)
    chunks, metas = [], []
    doc_name = getattr(file, "name", "document.pdf")
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            chunk = text[start:end]
            chunks.append(chunk)
            metas.append({"source": doc_name, "page": i + 1})
            start = end - overlap
            if start < 0:
                start = 0
            if end >= len(text):
                break
    return chunks, metas

# in services/rag.py
def build_context(snippets, lang_hint: str = "en") -> str:
    lines = []
    for txt, meta, score in snippets:
        src = meta.get("source", "N/A")
        if src.startswith("http"):
            lines.append(f"[{src}] {txt}")
        else:
            pg = meta.get("page","?")
            lines.append(f"[{src} p.{pg}] {txt}")
    return "\n\n".join(lines)

SYSTEM_PROMPT = """You are PGRKAM Ai Assistant. RULES:
-Answer ONLY with verified PGRKAM context.
- Answer ONLY using the provided context. If the context is insufficient, say you cannot find it and suggest the closest PGRKAM link.
- If no retrieved context is provided, refuse and direct to https://www.pgrkam.com."
"""

def rag_answer(vs: VectorStore, query: str, lang_hint: str, llm_fn, top_k: int = 5) -> str:
    hits = vs.search(query, k=top_k)
    if not hits:
        return "माफ़ कीजिए, इस विषय की जानकारी अभी संदर्भ में नहीं मिली। कृपया बाएँ साइडबार से PGRKAM की PDF/पेज जोड़ें और 'Build/Update Index' दबाएँ।"

    context = build_context(hits, lang_hint)
    cites = []
    for _, meta, _ in hits[:3]:
        s = meta.get("source","")
        cites.append(f"({s if s.startswith('http') else f'{s} p.{meta.get('page','?')}'})")
    cites = " ".join(dict.fromkeys(cites))

    user_prompt = (
        f"User language: {lang_hint}\n"
        f"Question: {query}\n\n"
        f"Context (must use):\n{context}\n\n"
        f"Instructions:\n- Use ONLY the context above.\n- Include citations like {cites}."
    )
    return llm_fn(SYSTEM_PROMPT, user_prompt)

