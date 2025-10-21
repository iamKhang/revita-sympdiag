from fastapi import FastAPI

app = FastAPI(title="Revita Symptom Diagnosis API", version="1.0.0")

@app.get("/docs")
async def get_docs():
    return {"message": "xin chào"}

@app.get("/")
async def root():
    return {"message": "Welcome to Revita Symptom Diagnosis API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
