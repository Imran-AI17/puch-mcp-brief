from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import time
import httpx

app = FastAPI(title="Puch Trust Brief MCP")

OWNER_PHONE = os.getenv("OWNER_PHONE", "919999999999")
VALIDATION_TOKEN = os.getenv("VALIDATION_TOKEN", "changeme")

class ValidateInput(BaseModel):
bearer_token: str

class ValidateOutput(BaseModel):
phone: str

class AnalyzeInput(BaseModel):
input: str

class Citation(BaseModel):
title: str
source: str
link: Optional[str] = None

class AnalyzeOutput(BaseModel):
verdict: str
bullets: List[str]
citations: List[Citation]
confidence: float
latency_ms: int

@app.get("/")
def health():
return {"status": "ok"}

@app.get("/mcp")
def mcp_metadata():
return {
"name": "puch-trust-brief",
"version": "0.1.0",
"tools": [
{"name": "validate", "schema": {"bearer_token": "string"}, "description": "Return owner phone in {country_code}{number} format."},
{"name": "analyze_claim", "schema": {"input": "string"}, "description": "Trust Brief for a text or URL."},
],
}

@app.post("/mcp/validate", response_model=ValidateOutput)
def validate(payload: ValidateInput):
if payload.bearer_token != VALIDATION_TOKEN:
raise HTTPException(status_code=401, detail="invalid bearer_token")
return ValidateOutput(phone=OWNER_PHONE)

@app.post("/mcp/analyze_claim", response_model=AnalyzeOutput)
def analyze_claim(payload: AnalyzeInput):
t0 = time.time()
text = (payload.input or "").strip()
citations: List[Citation] = []
bullets: List[str] = []
verdict = "unverified"
confidence = 0.4

if text.startswith("http://") or text.startswith("https://"):
    try:
        resp = httpx.get(text, timeout=6.0, follow_redirects=True)
        url = str(resp.url)
        html = resp.text or ""
        lo = html.lower()
        s = lo.find("<title>")
        e = lo.find("</title>")
        title = None
        if s != -1 and e != -1 and e > s:
            title = html[s + 7:e].strip()[:140]
        citations.append(Citation(title=title or "Source", source="Link", link=url))
        bullets.append("Scanned the linked page and extracted the title.")
    except Exception:
        bullets.append("Tried to fetch the link but timed out; treated as text.")
else:
    bullets.append("Processed as a text claim; no external link provided.")

bullets.append("MVP result: preliminary only, not a full fact-check.")
latency_ms = int((time.time() - t0) * 1000)
return AnalyzeOutput(
    verdict=verdict,
    bullets=bullets[:3],
    citations=citations[:1],
    confidence=confidence,
    latency_ms=latency_ms,
)
