from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
import os
from deep_translator import GoogleTranslator

app = FastAPI(title="Revita Symptom Diagnosis API", version="1.0.0")

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả domain
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép mọi phương thức (GET, POST, PUT, DELETE,...)
    allow_headers=["*"],  # Cho phép mọi header
)

# Lấy môi trường từ biến môi trường
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

# Load model and data
def load_model():
    if ENVIRONMENT == "production":
        # Production: load từ absolute path (mount từ volume)
        model_path = "/app/models/ovr_sgd_tfidf.joblib"
    else:
        # Development: load từ relative path
        model_path = os.path.join(os.path.dirname(__file__), "..", "models", "ovr_sgd_tfidf.joblib")
    
    bundle = joblib.load(model_path)
    return bundle

def load_icd_mapping():
    if ENVIRONMENT == "production":
        # Production: load từ absolute path (mount từ volume)
        data_path = "/app/models/d_icd_diagnoses.csv.gz"
    else:
        # Development: load từ relative path
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "mimiciv", "3.1", "hosp", "d_icd_diagnoses.csv.gz")
    
    d = pd.read_csv(data_path, compression="gzip", usecols=["icd_code","icd_version","long_title"])
    title_map = {(int(v), c.strip()): lt for c, v, lt in zip(d.icd_code, d.icd_version, d.long_title)}
    return title_map

# Default config
MAX_TOKENS = 8000  # Default value

# Load model and data once at startup
try:
    bundle = load_model()
    clf = bundle["clf"]
    word_vec = bundle["word_vec"]
    char_vec = bundle["char_vec"]
    mlb = bundle["mlb"]
    cfg = bundle["cfg"]
    MAX_TOKENS = cfg.get("MAX_TOKENS_PER_DOC", 8000)
    title_map = load_icd_mapping()
    model_loaded = True
except Exception as e:
    print(f"Error loading model: {e}")
    model_loaded = False

# Pydantic models
class PatientInfo(BaseModel):
    age: int
    gender: str
    notes: str

class DiseasePrediction(BaseModel):
    icd_code: str
    probability: float
    disease_name: str

class PredictionResponse(BaseModel):
    predictions: List[DiseasePrediction]
    patient_info: PatientInfo

class TranslationRequest(BaseModel):
    text: str

# Helper functions
def _truncate(s, mx=MAX_TOKENS):
    return " ".join(str(s).split()[:mx])

def _to_X(texts):
    s = pd.Series(texts).map(_truncate)
    Xw = word_vec.transform(s)
    if char_vec is not None:
        from scipy.sparse import hstack
        Xc = char_vec.transform(s)
        return hstack([Xw, Xc], format="csr")
    return Xw

def predict_topk(texts, K=5):
    P = clf.predict_proba(_to_X(texts))
    codes = mlb.classes_
    out = []
    for i in range(len(texts)):
        idx = np.argsort(-P[i])[:K]
        out.append([(codes[j], float(P[i,j])) for j in idx])
    return out

def icd_name_from_prefixed(code_with_prefix: str) -> str:
    try:
        ver_str, code = code_with_prefix.split("-", 1)
        return title_map.get((int(ver_str), code), "(unknown title)")
    except Exception:
        return "(unknown title)"

def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text to translate must not be empty.")
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        return translator.translate(text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Translation failed: {exc}")

# API endpoints
@app.get("/docs")
async def get_docs():
    return {"message": "xin chào"}

@app.get("/")
async def root():
    return {"message": "Welcome to Revita Symptom Diagnosis API"}

@app.post("/predict", response_model=PredictionResponse)
async def predict_disease(patient: PatientInfo):
    if not model_loaded:
        raise Exception("Model not loaded. Please check if model files exist.")
    
    # Combine patient info with notes for prediction
    combined_text = f"Age: {patient.age}, Gender: {patient.gender}. {patient.notes}"
    
    # Get predictions
    predictions = predict_topk([combined_text], K=10)[0]
    
    # Format response
    disease_predictions = []
    for code, probability in predictions:
        disease_name = icd_name_from_prefixed(code)
        disease_predictions.append(DiseasePrediction(
            icd_code=code,
            probability=probability,
            disease_name=disease_name
        ))
    
    return PredictionResponse(
        predictions=disease_predictions,
        patient_info=patient
    )

@app.post("/translate/en-vi")
async def translate_en_vi(payload: TranslationRequest):
    translated_text = translate_text(payload.text, "en", "vi")
    return {
        "source_language": "en",
        "target_language": "vi",
        "source_text": payload.text,
        "translated_text": translated_text,
    }

@app.post("/translate/vi-en")
async def translate_vi_en(payload: TranslationRequest):
    translated_text = translate_text(payload.text, "vi", "en")
    return {
        "source_language": "vi",
        "target_language": "en",
        "source_text": payload.text,
        "translated_text": translated_text,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
