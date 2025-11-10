# services/ingest.py
import time, re, json
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PGRKAM-RAG/1.0; +research-use)"
}

# ---------- Helpers ----------
def _clean_text(t: str) -> str:
    t = re.sub(r"\s+", " ", t or "").strip()
    return t

def _fetch(url: str, timeout=20):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text

def _is_same_host(seed:str, href:str)->bool:
    try:
        return urlparse(seed).netloc == urlparse(href).netloc
    except:
        return False

# ---------- Simple site crawl (breadth-first, limited) ----------
def crawl(seed_urls, max_pages=40, allow_paths=None):
    """
    seed_urls: list of starting URLs on pgrkam.com
    allow_paths: list of substrings that must appear in URL (e.g., ["/job", "/training"])
    """
    seen, queue = set(), list(seed_urls)
    pages = []

    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            html = _fetch(url)
        except Exception:
            continue

        soup = BeautifulSoup(html, "html.parser")

        # extract page text
        # keep visible text; drop nav/script/style
        for s in soup(["script","style","noscript"]):
            s.extract()
        text = _clean_text(soup.get_text(" "))

        title = _clean_text(soup.title.get_text()) if soup.title else ""
        pages.append({
            "url": url,
            "title": title or url,
            "text": text,
            "ts": int(time.time())
        })

        # discover new links
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            if href.startswith("mailto:") or href.startswith("tel:"):
                continue
            if not _is_same_host(seed_urls[0], href):
                continue
            if allow_paths and not any(p in href for p in allow_paths):
                continue
            if href not in seen and len(pages) + len(queue) < max_pages:
                queue.append(href)

    return pages

def save_jsonl(pages, out_path="data/pgrkam_pages.jsonl"):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for p in pages:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    return out_path

def jsonl_to_chunks(jsonl_path):
    """Return (chunks, metas) compatible with your VectorStore.build"""
    chunks, metas = [], []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            url = obj.get("url","")
            title = obj.get("title","")
            text = obj.get("text","")
            if not text: 
                continue
            # naive chunking ~800-1200 chars
            step = 1000
            for i in range(0, len(text), step):
                piece = text[i:i+step]
                if len(piece) < 200:
                    continue
                chunks.append(piece)
                metas.append({"source_url": url, "title": title})
    return chunks, metas

def ingest_from_web(
    seed_urls,
    allow_paths=None,
    max_pages=40,
    jsonl_out="data/pgrkam_pages.jsonl"
):
    pages = crawl(seed_urls, max_pages=max_pages, allow_paths=allow_paths)
    path = save_jsonl(pages, jsonl_out)
    return path
