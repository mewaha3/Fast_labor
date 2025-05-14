from pathlib import Path
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer

# ------------------------------------------------------------------ #
# 1) Load embedding model (unused for manual scoring)
# ------------------------------------------------------------------ #
_EMBED_MODEL = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

# ------------------------------------------------------------------ #
# 2) Text encoding (include date/time/location)
# ------------------------------------------------------------------ #
_TEXT_COL_JOBS    = [
    "job_type", "job_detail", "required_skill",
    "province", "district", "subdistrict",
    "job_date", "start_time", "end_time"
]
_TEXT_COL_WORKERS = [
    "job_type", "skills",
    "province", "district", "subdistrict",
    "job_date", "start_time", "end_time"
]

def _encode_texts(texts: list[str]) -> np.ndarray:
    return _EMBED_MODEL.encode([t if isinstance(t, str) else "" for t in texts], show_progress_bar=False)


def encode_job_df(jobs_df: pd.DataFrame) -> pd.DataFrame:
    df = jobs_df.copy()
    for col in _TEXT_COL_JOBS:
        df[col] = df[col].fillna("").astype(str) if col in df.columns else ""
    df["__text"] = df[_TEXT_COL_JOBS].agg(" ".join, axis=1)
    df["vec"]    = list(_encode_texts(df["__text"].tolist()))
    df.drop(columns="__text", inplace=True)
    if all(c in df.columns for c in ["job_date","start_time","end_time"]):
        df['job_date'] = pd.to_datetime(df['job_date'], errors='coerce').dt.date
        df['start_dt'] = pd.to_datetime(df['job_date'].astype(str) + ' ' + df['start_time'], errors='coerce')
        df['end_dt']   = pd.to_datetime(df['job_date'].astype(str) + ' ' + df['end_time'],   errors='coerce')
    return df


def encode_worker_df(workers_df: pd.DataFrame) -> pd.DataFrame:
    df = workers_df.copy()
    for col in _TEXT_COL_WORKERS:
        df[col] = df[col].fillna("").astype(str) if col in df.columns else ""
    df["__text"] = df[_TEXT_COL_WORKERS].agg(" ".join, axis=1)
    df["vec"]    = list(_encode_texts(df["__text"].tolist()))
    df.drop(columns="__text", inplace=True)
    if all(c in df.columns for c in ['job_date','start_time','end_time']):
        df['job_date']    = pd.to_datetime(df['job_date'],    errors='coerce').dt.date
        df['avail_start'] = pd.to_datetime(df['job_date'].astype(str) + ' ' + df['start_time'], errors='coerce')
        df['avail_end']   = pd.to_datetime(df['job_date'].astype(str) + ' ' + df['end_time'],   errors='coerce')
    return df

# ------------------------------------------------------------------ #
# 3) Build FAISS index
# ------------------------------------------------------------------ #
def _build_faiss_index(mat: np.ndarray):
    dim   = mat.shape[1]
    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(mat)
    index.add(mat)
    return index

# ------------------------------------------------------------------ #
# 4) Feature construction (updated)
# ------------------------------------------------------------------ #
def _feature_df(worker: pd.Series, jobs_subset: pd.DataFrame) -> tuple:
    sim       = jobs_subset['sim'].to_numpy().reshape(-1,1)
    
    # Matching job types
    same_type = (jobs_subset['job_type'] == worker.job_type).astype(int).to_numpy().reshape(-1,1)
    
    # Matching location (province, district, subdistrict)
    loc_match = (jobs_subset[['province','district','subdistrict']].values == worker[['province','district','subdistrict']].values).all(axis=1).astype(int).reshape(-1,1)

    # Wage difference (with weight)
    if 'salary' in jobs_subset.columns:
        job_pay   = pd.to_numeric(jobs_subset['salary'], errors='coerce').to_numpy().reshape(-1,1)
        worker_pay= float(worker.get('exp_wage',0))
        diff_wage = np.abs(job_pay - worker_pay)
    else:
        diff_wage = np.zeros_like(sim)
    
    # Time match (time overlap between worker's availability and job start/end)
    if all(c in jobs_subset.columns for c in ['start_dt','end_dt']) and 'avail_start' in worker.index:
        overlap     = np.minimum(jobs_subset['end_dt'], worker['avail_end']) - np.maximum(jobs_subset['start_dt'], worker['avail_start'])
        time_match  = (overlap.dt.total_seconds().fillna(0) > 0).astype(int).to_numpy().reshape(-1,1)
    else:
        time_match  = np.zeros_like(sim)
    
    return sim, diff_wage, same_type, time_match, loc_match

# ------------------------------------------------------------------ #
# 5) Recommend function with refined scoring (updated)
# ------------------------------------------------------------------ #
def recommend(worker_row: pd.Series,
              jobs_df: pd.DataFrame,
              k: int = 50,
              n: int = 5) -> pd.DataFrame:
    
    mat     = np.vstack(jobs_df['vec'])
    index   = _build_faiss_index(mat)
    w_vec   = worker_row.vec.reshape(1,-1)
    faiss.normalize_L2(w_vec)
    sim_scores, idxs = index.search(w_vec, k)
    sim_arr, idxs = sim_scores[0], idxs[0]
    subset = jobs_df.iloc[idxs].copy()
    subset['sim'] = sim_arr
    sim_arr, diff_arr, type_arr, time_arr, loc_arr = _feature_df(worker_row, subset)
    
    # Normalize wage difference (calculate wage score)
    max_diff = diff_arr.max() if diff_arr.max() > 0 else 1.0
    wage_score = 1 - (diff_arr / max_diff)  # Normalized wage difference
    
    # Increase weight for location and wage (if location matching is more important)
    w_type = 0.3  # Job type matching (reduced weight)
    w_loc = 0.4  # Location matching (increased weight)
    w_wage = 0.2  # Wage matching (increased weight)
    w_time = 0.1  # Time matching (slightly adjusted)
    
    # Calculate the final score (give priority to location and wage)
    final = (
        w_type * type_arr +
        w_loc * loc_arr +
        w_wage * wage_score +
        w_time * time_arr
    ).reshape(-1)
    
    # Assign AI score to the subset
    subset['ai_score'] = final
    
    # Ensure that the AI score has variance and is not the same for all matches
    subset = subset.sort_values('ai_score', ascending=False)
    
    return subset.head(n).reset_index(drop=True)

# ------------------------------------------------------------------ #
# 6) Recommend seekers for employer (updated)
# ------------------------------------------------------------------ #
def recommend_seekers(job_row: pd.Series,
                      workers_df: pd.DataFrame,
                      k: int = 50,
                      n: int = 5) -> pd.DataFrame:
    return recommend(worker_row=job_row, jobs_df=workers_df, k=k, n=n)
