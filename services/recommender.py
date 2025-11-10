# services/recommender.py
import pandas as pd
import numpy as np
from typing import Dict, List
from services.embeddings import embed_texts, embed_one

def load_jobs_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    needed = ["id","title","location","sector","description","url","deadline"]
    for col in needed:
        if col not in df.columns:
            df[col] = ""
    return df

def make_recs(df: pd.DataFrame, prefs: Dict, top_k: int = 5) -> pd.DataFrame:
    # Build text blobs
    job_texts = (df["title"].fillna("") + " | " +
                 df["sector"].fillna("") + " | " +
                 df["location"].fillna("") + " | " +
                 df["description"].fillna("")).tolist()
    job_vecs = embed_texts(job_texts)

    pref_str = " ".join([
        "role:" + ",".join(prefs.get("roles", [])),
        "sector:" + ",".join(prefs.get("sectors", [])),
        "location:" + ",".join(prefs.get("locations", [])),
        "degree:" + prefs.get("degree",""),
        "exp:" + str(prefs.get("experience",""))
    ])
    q = embed_one(pref_str).reshape(1,-1)
    sims = (job_vecs @ q.T).ravel()
    top_idx = np.argsort(-sims)[:top_k]
    out = df.iloc[top_idx].copy()
    out["score"] = sims[top_idx]
    return out.sort_values("score", ascending=False)
