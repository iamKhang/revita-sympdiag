# %% [1] CONFIG — centralize all knobs (with explanations)
from pathlib import Path

# I/O
BASE_INPUT = Path("/kaggle/input/mimic-iv-proc-revita-2025-09-222")  # dataset root
PROC       = BASE_INPUT
UNIFIED_PQT = PROC / "train_unified.parquet"  # unified training file (preferred)
UNIFIED_CSV = PROC / "train_unified.csv"      # fallback
WORK_DIR    = Path("/kaggle/working")

# Label selection
MIN_LABEL_FREQ = 10  # only keep ICD labels with frequency > 200 (tighter to save RAM)      # drop ultra-rare ICDs (< this admissions frequency)
MAX_LABELS     = 2000     # keep top-K most frequent ICDs after thresholding

# Text cleanup / limits
MAX_TOKENS_PER_DOC = 8000 # cap tokens per doc before vectorization (higher than before)

# Vectorization (TF–IDF for better weighting versus hashing)
USE_CHAR_NGRAMS   = False             # add char n-grams for OOV robustness
WORD_NGRAM_RANGE  = (1, 2)            # word n-grams
CHAR_NGRAM_RANGE  = (3, 5)            # char n-grams (if enabled)
MAX_FEATURES_WORD = 400_000           # smaller vocabulary to cut RAM/size           # cap vocabulary size for words (RAM-aware)
MAX_FEATURES_CHAR = 10_000           # cap for chars (if enabled)
SUBLINEAR_TF      = True              # log(1+tf)
MIN_DF            = 2                 # prune ultra-rare terms

# Model (One-vs-Rest on logistic SGD)
ALPHA         = 1e-5      # L2 regularization strength
EARLY_STOP    = True      # use built-in early stopping (per label)
VAL_FRACTION  = 0.1       # fraction from training for early stopping
N_JOBS        = 1         # single worker to avoid extra RAM copies on Kaggle free        # parallel OvR heads (where supported)

# Train / Eval
TEST_SIZE           = 0.15  # patient-level test split
VAL_SIZE_WITHIN_TRAIN = 0.1765 # ≈ 15% of total (so train/val/test ≈ 70/15/15)

# Quick smoke-test limit (set e.g. 1000 to train fast on a small subset). None = use all
LIMIT_SAMPLES      = None

TOPK              = 10
SEED              = 40

# Artifacts
CKPT_MODEL = WORK_DIR / "ovr_sgd_tfidf.joblib"  # model + vectorizers + label binarizer
PRECOMP_DIR = WORK_DIR / "precomp_sparse"       # cache sparse matrices
PRECOMP_DIR.mkdir(parents=True, exist_ok=True)

print({
    "dataset": str(BASE_INPUT),
    "unified": str(UNIFIED_PQT if UNIFIED_PQT.exists() else UNIFIED_CSV),
    "MAX_FEATURES_WORD": MAX_FEATURES_WORD,
    "USE_CHAR_NGRAMS": USE_CHAR_NGRAMS,
    "MIN_LABEL_FREQ": MIN_LABEL_FREQ,
    "MAX_LABELS": MAX_LABELS,
    "CKPT_MODEL": str(CKPT_MODEL),
})

# %% [2] LOAD unified dataframe
import pandas as pd
if UNIFIED_PQT.exists():
    df = pd.read_parquet(UNIFIED_PQT)
elif UNIFIED_CSV.exists():
    df = pd.read_csv(UNIFIED_CSV)
else:
    raise FileNotFoundError("Không thấy train_unified.{parquet|csv} ở gốc dataset.")

# Normalize & light clean
def truncate_tokens(text: str, mx:int=MAX_TOKENS_PER_DOC):
    return " ".join(str(text).split()[:mx])

df["text_clean"] = df["text_clean"].map(truncate_tokens)
df["icd_codes_list"] = df["icd_codes"].astype(str).str.split(";")
print("Loaded:", df.shape)

# %% [3] LABEL SELECTION — prefer precomputed freq file
from collections import Counter
freq_csv = (PROC/"top_icd_coverage.csv") if (PROC/"top_icd_coverage.csv").exists() else (PROC/"icd_hadm_freq.csv")
if freq_csv.exists():
    freq = pd.read_csv(freq_csv)
    if "icd_full" not in freq.columns:
        if freq.columns.tolist() == ["index","hadm_freq"]:
            freq = freq.rename(columns={"index":"icd_full"})
        else:
            freq.columns = ["icd_full","hadm_freq"]
    keep_df = (freq[freq["hadm_freq"] >= MIN_LABEL_FREQ]
               .sort_values("hadm_freq", ascending=False).head(MAX_LABELS))
    KEEP_LABELS = set(keep_df["icd_full"].tolist())
    print(f"Reuse nhãn từ {freq_csv.name}: {len(KEEP_LABELS)} labels")
else:
    cnt = Counter(c for row in df["icd_codes_list"] for c in row)
    keep = [c for c,n in cnt.items() if n >= MIN_LABEL_FREQ]
    keep = sorted(keep, key=lambda c: cnt[c], reverse=True)[:MAX_LABELS]
    KEEP_LABELS = set(keep)
    print(f"Tính nhãn từ unified: {len(KEEP_LABELS)} labels")

# Filter rows & form labels field
mask = df["icd_codes_list"].map(lambda L: any(c in KEEP_LABELS for c in L))
df = df.loc[mask].copy()
df["labels"] = df["icd_codes_list"].map(lambda L: [c for c in L if c in KEEP_LABELS])
print("After label filter:", df.shape)

# Optional: downsample for quick syntax/logic smoke tests
if LIMIT_SAMPLES is not None and len(df) > LIMIT_SAMPLES:
    df = df.sample(LIMIT_SAMPLES, random_state=SEED).reset_index(drop=True)
    print(f"Downsampled to {len(df)} rows for quick test")

# %% [4] PATIENT-LEVEL SPLIT (no leakage)
from sklearn.model_selection import GroupShuffleSplit

# test split
gss1 = GroupShuffleSplit(n_splits=1, test_size=TEST_SIZE, random_state=SEED)
idx_tr, idx_te = next(gss1.split(df, groups=df["subject_id"]))
train_val = df.iloc[idx_tr].reset_index(drop=True)
test = df.iloc[idx_te].reset_index(drop=True)

# val split inside train
gss2 = GroupShuffleSplit(n_splits=1, test_size=VAL_SIZE_WITHIN_TRAIN, random_state=SEED)
idx_tr2, idx_va = next(gss2.split(train_val, groups=train_val["subject_id"]))
train = train_val.iloc[idx_tr2].reset_index(drop=True)
val   = train_val.iloc[idx_va].reset_index(drop=True)
print({"train": len(train), "val": len(val), "test": len(test)})

# %% [5] VECTORIZATION — TF‑IDF (fit once, transform once, cache)
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy import sparse
import joblib

word_vec = TfidfVectorizer(
    ngram_range=WORD_NGRAM_RANGE,
    max_features=MAX_FEATURES_WORD,
    min_df=MIN_DF,
    sublinear_tf=SUBLINEAR_TF,
    norm="l2",
    dtype=np.float32,
)

char_vec = None
if USE_CHAR_NGRAMS:
    char_vec = TfidfVectorizer(
        analyzer="char",
        ngram_range=CHAR_NGRAM_RANGE,
        max_features=MAX_FEATURES_CHAR,
        min_df=MIN_DF,
        sublinear_tf=SUBLINEAR_TF,
        norm="l2",
        dtype=np.float32,
    )

# Fit on TRAIN ONLY (avoid leakage)
word_vec.fit(train["text_clean"]) 
Xtr_w = word_vec.transform(train["text_clean"]) 
Xva_w = word_vec.transform(val["text_clean"]) 
Xte_w = word_vec.transform(test["text_clean"]) 

if USE_CHAR_NGRAMS:
    char_vec.fit(train["text_clean"]) 
    Xtr_c = char_vec.transform(train["text_clean"]) 
    Xva_c = char_vec.transform(val["text_clean"]) 
    Xte_c = char_vec.transform(test["text_clean"]) 
    Xtr = sparse.hstack([Xtr_w, Xtr_c], format="csr")
    Xva = sparse.hstack([Xva_w, Xva_c], format="csr")
    Xte = sparse.hstack([Xte_w, Xte_c], format="csr")
else:
    Xtr, Xva, Xte = Xtr_w.tocsr(), Xva_w.tocsr(), Xte_w.tocsr()

# Binarize labels (fix order)
from sklearn.preprocessing import MultiLabelBinarizer
mlb = MultiLabelBinarizer()
mlb.fit(train["labels"])  # establishes class order
Ytr = mlb.transform(train["labels"]).astype("int8")
Yva = mlb.transform(val["labels"]).astype("int8")
Yte = mlb.transform(test["labels"]).astype("int8")

# Guard: drop labels that have <2 positives in TRAIN (required by Stratified CV used in early_stopping)
import numpy as np
pos_counts = np.asarray(Ytr.sum(axis=0)).ravel() if hasattr(Ytr, "toarray") else Ytr.sum(axis=0)
mask_cols = pos_counts >= 2
if mask_cols.sum() < len(mask_cols):
    kept_classes = mlb.classes_[mask_cols]
    mlb = MultiLabelBinarizer(classes=kept_classes)
    mlb.fit([kept_classes])
    Ytr = mlb.transform(train["labels"]).astype("int8")
    Yva = mlb.transform(val["labels"]).astype("int8")
    Yte = mlb.transform(test["labels"]).astype("int8")
    print(f"Filtered labels with <2 positives in TRAIN: now {len(kept_classes)} classes")

# Optionally cache
# NOTE: skip caching giant sparse matrices to save disk/RAM on Kaggle free
# (no X cache written)

# %% [6] TRAIN — OneVsRest + SGD (logistic), early stopping
from sklearn.linear_model import SGDClassifier
from sklearn.multiclass import OneVsRestClassifier

base = SGDClassifier(
    loss="log_loss",
    penalty="l2",
    alpha=ALPHA,
    learning_rate="optimal",
    early_stopping=(EARLY_STOP and (LIMIT_SAMPLES is None)),
    validation_fraction=VAL_FRACTION,
    n_iter_no_change=3,
    class_weight=None,
    random_state=SEED,
)

clf = OneVsRestClassifier(base, n_jobs=N_JOBS, verbose=1)
clf.fit(Xtr, Ytr)

# %% [7] SAVE ARTIFACTS (shrink to float32)
for est in getattr(clf, "estimators_", []):
    if hasattr(est, "coef_"):
        est.coef_ = est.coef_.astype("float32", copy=False)
    if hasattr(est, "intercept_"):
        est.intercept_ = est.intercept_.astype("float32", copy=False)

joblib.dump({
    "clf": clf,
    "word_vec": word_vec,
    "char_vec": char_vec,
    "mlb": mlb,
    "cfg": {
        "WORD_NGRAM_RANGE": WORD_NGRAM_RANGE,
        "CHAR_NGRAM_RANGE": CHAR_NGRAM_RANGE,
        "MAX_FEATURES_WORD": MAX_FEATURES_WORD,
        "MAX_FEATURES_CHAR": MAX_FEATURES_CHAR,
        "SUBLINEAR_TF": SUBLINEAR_TF,
        "MIN_DF": MIN_DF,
        "ALPHA": ALPHA,
        "EARLY_STOP": EARLY_STOP,
        "VAL_FRACTION": VAL_FRACTION,
        "TOPK": TOPK,
        "SEED": SEED,
    }
}, CKPT_MODEL, compress=3)
print("Saved model →", CKPT_MODEL)

# %% [10] INFERENCE helper
import pandas as pd

def predict_topk(texts, K=TOPK):
    s = pd.Series(texts).map(truncate_tokens)
    Xw = word_vec.transform(s)
    if char_vec is not None:
        from scipy.sparse import hstack
        Xc = char_vec.transform(s)
        X = hstack([Xw, Xc], format="csr")
    else:
        X = Xw
    P = clf.predict_proba(X)
    codes = mlb.classes_
    out = []
    for i in range(len(texts)):
        idx = np.argsort(-P[i])[:K]
        out.append([(codes[j], float(P[i,j])) for j in idx])
    return out

# %% [11] DEMO & EXPORT small sample
samples = [
    "Service: MEDICINE\nHistory: chest pain, HTN, DM, hyperlipidemia...",
    "Service: SURGERY\nPost-op day #2, fever, wound infection, antibiotics...",
]
for i, preds in enumerate(predict_topk(samples, K=TOPK), 1):
    print(f"\nCase {i}:")
    for code, prob in preds:
        print(f"  {code}: {prob:.3f}")

# optional: export 50 predictions from TEST
out = []
for i in range(min(50, len(test))):
    srow = test.iloc[i]
    topk = predict_topk([srow["text_clean"]], K=TOPK)[0]
    out.append({
        "subject_id": srow["subject_id"],
        "hadm_id": srow["hadm_id"],
        "gold": ";".join(srow["labels"]),
        "pred_topK": ";".join([f"{c}:{p:.3f}" for c,p in topk])
    })
pd.DataFrame(out).to_csv(WORK_DIR/"preds_sample.csv", index=False)
print("Saved:", WORK_DIR/"preds_sample.csv")