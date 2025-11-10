# services/crawl.py
import re, time, requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (edu project)"}

def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script","style","noscript","header","footer","nav","iframe"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()

def same_domain(url, allowed_domain):
    return urlparse(url).netloc.endswith(allowed_domain)

def crawl_urls(seeds, allowed_domain="pgrkam.com", max_pages=30, timeout=15):
    seen, pages = set(), []
    queue = [s.strip() for s in seeds if s.strip()]
    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        if url in seen: continue
        seen.add(url)
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code != 200 or "text/html" not in r.headers.get("Content-Type",""):
                continue
            text = clean_text(r.text)
            if len(text) < 200:  # skip tiny pages
                continue
            pages.append({"url": url, "text": text})
            # discover new links
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select("a[href]"):
                nxt = urljoin(url, a["href"])
                if nxt.startswith("mailto:") or nxt.startswith("tel:"): 
                    continue
                if same_domain(nxt, allowed_domain) and nxt not in seen and len(queue) < 200:
                    queue.append(nxt)
            time.sleep(0.2)
        except Exception:
            continue
    return pages

def chunk_pages(pages, max_chars=1200, overlap=200):
    chunks, metas = [], []
    for p in pages:
        t = p["text"]
        start = 0
        while start < len(t):
            end = min(start + max_chars, len(t))
            chunk = t[start:end]
            chunks.append(chunk)
            metas.append({"source": p["url"]})
            if end >= len(t): break
            start = end - overlap
            if start < 0: start = 0
    return chunks, metas
