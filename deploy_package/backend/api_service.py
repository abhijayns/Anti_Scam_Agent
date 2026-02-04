import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from agent_wrapper import AntiScamAgent

import uvicorn

# Load environment variables
load_dotenv()

app = FastAPI(title="Anti-Scam Agent API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = AntiScamAgent()

class AnalyzeRequest(BaseModel):
    text: str

@app.post("/analyze")
async def analyze_text(request: AnalyzeRequest):
    try:
        result = await agent.analyze(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
