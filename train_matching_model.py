# train_matching_model.py
"""
Train LightGBM LambdaRank + Embedding Similarity
Creates `matching.lgb` next to `matching.py` with 5 features:
  1) sim          -> semantic cosine similarity
  2) diff_wage    -> absolute wage difference
  3) same_type    -> job_type match flag
  4) time_overlap -> datetime overlap flag
  5) loc_match    -> location match flag

Requires CSVs in the same folder:
  • post_job.csv
  • find_job.csv
  • history_matches.csv
"""

from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from datetime import datetime, timedelta

# ------------------------------------------------------------------
# 1) Paths & constants
# ------------------------------------------------------------------
ROOT = Path(__file__).parent
MODEL_PATH = ROOT / "matching.lgb"

POST_JOB_CSV      = ROOT / "post_job.csv"
FIND_JOB_CSV      = ROOT / "find_job.csv"
HISTORY_MATCH_CSV = ROOT / "history_matches.csv"

EMBED_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

# ------------------------------------------------------------------
# 2) Load CSVs and convert date/time columns
# ------------------------------------------------------------------
for p in (POST_JOB_CSV, FIND_JOB_CSV, HISTORY_MATCH_CSV):
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")

print("🔄 Loading CSVs …")
jobs    = pd.read_csv(POST_JOB_CSV)
workers = pd.read_csv(FIND_JOB_CSV)
hist    = pd.read_csv(HISTORY_MATCH_CSV)

# Convert job_date to date and times to time objects
jobs["job_date"]    = pd.to_datetime(jobs["job_date"], errors="coerce").dt.date
workers["job_date"] = pd.to_datetime(workers["job_date"], errors="coerce").dt.date
for df in (jobs, workers):
    for col in ("start_time", "end_time"):
        df[col] = (
            pd.to_datetime(df[col], format="%H:%M:%S", errors="coerce").dt.time
        )

# ------------------------------------------------------------------
# 3) Encode embeddings
# ------------------------------------------------------------------
print("🔄 Encoding embeddings…")
embedder = SentenceTransformer(EMBED_MODEL_NAME)

def embed_text(df: pd.DataFrame, cols: list[str], new_col: str) -> pd.DataFrame:
    texts = df[cols].fillna("").agg(" ".join, axis=1).tolist()
    vecs  = embedder.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    df[new_col] = list(vecs)
    return df

jobs    = embed_text(jobs,    ["job_type", "job_detail"], "v_job")
workers = embed_text(workers, ["job_type", "skills"], "v_worker")

# ------------------------------------------------------------------
# 4) Merge tables: history → jobs → workers
# ------------------------------------------------------------------
print("🔄 Merging tables…")
tmp  = hist.merge(jobs,    on="job_id",    how="inner", suffixes=("", "_job"))
full = tmp.merge(workers,   on="worker_id", how="inner", suffixes=("", "_worker"))

# ------------------------------------------------------------------
# 5) Rename job columns to have _job suffix for datetime/location
# ------------------------------------------------------------------
full = full.rename(columns={
    "job_date":    "job_date_job",
    "start_time":  "start_time_job",
    "end_time":    "end_time_job",
    "province":    "province_job",
    "district":    "district_job",
    "subdistrict": "subdistrict_job"
})

# ------------------------------------------------------------------
# 6) Validate required columns
# ------------------------------------------------------------------
REQ_COLS = [
    "v_job", "v_worker",
    "salary", "start_salary", "range_salary",
    "job_type", "job_type_worker",
    "job_date_job", "start_time_job", "end_time_job",
    "job_date_worker", "start_time_worker", "end_time_worker",
    "province_job", "district_job", "subdistrict_job",
    "province_worker", "district_worker", "subdistrict_worker",
]
missing = [c for c in REQ_COLS if c not in full.columns]
if missing:
    raise KeyError(f"Missing columns after merge: {missing}")

# ------------------------------------------------------------------
# 7) Build feature matrix X, label y, and group sizes
# ------------------------------------------------------------------
print("🔄 Building feature matrix…")
def cosine(a: np.ndarray, b: np.ndarray) -> float:
    a_norm = a / (np.linalg.norm(a) + 1e-9)
    b_norm = b / (np.linalg.norm(b) + 1e-9)
    return float(a_norm @ b_norm)

X_list, y_list, group_sizes = [], [], []
current_q = None
for row in tqdm(full.itertuples(index=False), total=len(full), desc="Rows"):
    # 1) sim
    sim = cosine(np.asarray(row.v_job), np.asarray(row.v_worker))
    # 2) diff_wage
    exp_wage = (row.start_salary + row.range_salary)/2 if row.range_salary > 0 else row.start_salary
    diff_wage = abs(row.salary - exp_wage)
    # 3) same_type
    same_type = int(str(row.job_type_worker).strip().lower() == str(row.job_type).strip().lower())
    # 4) time_overlap
    jd = datetime.combine(row.job_date_job,    row.start_time_job)
    je = datetime.combine(row.job_date_job,    row.end_time_job)
    wd = datetime.combine(row.job_date_worker, row.start_time_worker)
    we = datetime.combine(row.job_date_worker, row.end_time_worker)
    overlap = max(timedelta(0), min(je, we) - max(jd, wd))
    time_ov = int(overlap.total_seconds() > 0)
    # 5) loc_match
    loc_match = int(
        (row.province_job, row.district_job, row.subdistrict_job) ==
        (row.province_worker, row.district_worker, row.subdistrict_worker)
    )

    X_list.append([sim, diff_wage, same_type, time_ov, loc_match])
    y_list.append(int(row.accepted))

    # group by query_id
    if row.query_id != current_q:
        group_sizes.append(0)
        current_q = row.query_id
    group_sizes[-1] += 1

X = np.asarray(X_list, dtype="float32")
y = np.asarray(y_list, dtype="float32")

# ------------------------------------------------------------------
# 8) Train LightGBM LambdaRanker
# ------------------------------------------------------------------
print("🔄 Training LightGBM LambdaRank model…")
ranker = lgb.LGBMRanker(
    objective="lambdarank",
    metric="ndcg",
    n_estimators=200,
    learning_rate=0.1,
    importance_type="gain",
)
ranker.fit(X, y, group=group_sizes)

# ------------------------------------------------------------------
# 9) Save model
# ------------------------------------------------------------------
ranker.booster_.save_model(str(MODEL_PATH))
print(f"✅ Saved model → {MODEL_PATH.resolve()}")
