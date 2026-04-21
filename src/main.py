from fastapi import FastAPI

app = FastAPI(title="Energy Auditor")

@app.get("/")
def root():
      return {"status": "up"}