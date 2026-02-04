"""
Anti-Scam Sentinel API - Main Application
FastAPI server with zero-latency perception, rate limiting, and forensics
Enhanced with async background processing for <300ms responses
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional, List
import asyncio
import time
from datetime import datetime
import logging

# Rate limiting
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    RATE_LIMIT_AVAILABLE = True
except ImportError:
    RATE_LIMIT_AVAILABLE = False

from agent.detector import ScamDetector
from agent.orchestrator import ConversationOrchestrator, ConversationPhase
from agent.extractor import IntelligenceExtractor
from agent.session_manager import SessionManager
from agent.metrics import MetricsCollector
from agent.models import (
    MessageRequest, AgentResponse, ExtractedEntities, Forensics, 
    ResponseMetadata, LegacyMessageEvent, LegacyAgentResponse, BankAccount,
    ValidatedUPI, TypingBehavior
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Anti-Scam Sentinel API",
    version="2.0.0",
    description="Intelligent honeypot agent for scam detection and intelligence extraction"
)

# Rate limiting setup
if RATE_LIMIT_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("✓ Rate limiting enabled")
else:
    limiter = None
    logger.warning("SlowAPI not installed - rate limiting disabled")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
from agent_wrapper import AntiScamAgent
agent = AntiScamAgent()
metrics = MetricsCollector()


# =============================================================================
# MIDDLEWARE
# =============================================================================

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to all responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(int(process_time * 1000))
    return response


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.on_event("startup")
async def startup_event():
    await agent.initialize()
    logger.info("✓ Anti-Scam Honeypot Agent initialized")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "honeypot_mode": "active"}


# =============================================================================
# MAIN MESSAGE ENDPOINT (ZERO-LATENCY VERSION)
# =============================================================================

@app.post("/engage")
@app.post("/analyze")
async def engage_scammer(event: MessageRequest):
    """
    Honeypot/Analysis Engagement Endpoint
    """
    try:
        # Normalize: event.text might be used by old callers, event.message by new
        message = getattr(event, 'message', getattr(event, 'text', None))
        if not message:
            raise HTTPException(status_code=400, detail="Message content required")
            
        result = await agent.engage(event.session_id, message)
        return result
    except Exception as e:
        logger.error(f"Engagement error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simulate")
async def simulate_loop(session_id: str, scam_type: str = "job_scam"):
    """
    Simulate a full back-and-forth between agent and scammer
    """
    from agent.simulator import ScammerSimulator
    simulator = ScammerSimulator(scam_type)
    
    conversation = []
    current_message = simulator.generate_message()
    
    for i in range(5): # Limit to 5 turns for testing
        conversation.append({"role": "scammer", "content": current_message})
        result = await agent.engage(session_id, current_message)
        agent_reply = result['agent_response']
        conversation.append({"role": "agent", "content": agent_reply})
        
        # Get next scammer message based on agent reply (mocked)
        current_message = simulator.generate_message(agent_reply)
        
    return {
        "session_id": session_id,
        "scam_type": scam_type,
        "history": conversation,
        "extracted": (await agent.session_manager.load_session(session_id))['intelligence']
    }


# =============================================================================
# LEGACY ENDPOINT (for backward compatibility)
# =============================================================================

@app.post("/message-event", response_model=LegacyAgentResponse)
async def handle_message_legacy(
    request: Request,
    event: LegacyMessageEvent,
    background_tasks: BackgroundTasks
):
    """
    Legacy API endpoint - maintains backward compatibility
    """
    # Convert to new format
    new_request = MessageRequest(
        session_id=event.session_id,
        message=event.message,
        timestamp=event.timestamp
    )
    
    # Call new endpoint
    response = await handle_message_v2(request, new_request, background_tasks)
    
    # Convert back to legacy format
    intel_dict = {
        'upi_ids': response.extracted_entities.upi_ids,
        'bank_accounts': [acc.model_dump() for acc in response.extracted_entities.bank_accounts],
        'urls': response.extracted_entities.urls,
        'phone_numbers': response.extracted_entities.phone_numbers,
        'amounts': response.extracted_entities.amounts,
        'emails': response.extracted_entities.emails
    }
    
    return LegacyAgentResponse(
        session_id=response.session_id,
        agent_message=response.agent_response,
        detected=response.is_scam,
        intelligence=intel_dict,
        metadata={
            'phase': response.metadata.phase,
            'persona': response.metadata.persona,
            'turn_count': response.metadata.turn_count,
            'scam_type': response.forensics.scam_type,
            'confidence': response.confidence_score,
            'latency_ms': response.metadata.latency_ms
        }
    )


# =============================================================================
# METRICS & SESSION ENDPOINTS
# =============================================================================

@app.get("/metrics")
async def get_metrics():
    """Get current performance metrics"""
    return await metrics.get_summary()


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session details (for debugging)"""
    session = await session_manager.load_session(session_id)
    return {
        "session_id": session_id,
        "phase": session.get('current_phase'),
        "persona": session.get('persona'),
        "scam_detected": session.get('scam_detected'),
        "turn_count": len(session.get('conversation_history', [])),
        "intelligence": session.get('intelligence'),
        "conversation": session.get('conversation_history', [])[-5:]
    }


# =============================================================================
# ANALYTICS ENDPOINT
# =============================================================================

from agent.analytics import (
    scammer_profiler, webhook_manager, analytics_builder,
    SessionAnalytics, ScammerProfile, ProfileMatch, WebhookConfig
)

@app.get("/analytics/{session_id}", response_model=SessionAnalytics)
async def get_session_analytics(session_id: str):
    """
    Get detailed analytics for a session
    Includes: timeline, indicators, intelligence score, profile link
    """
    session = await session_manager.load_session(session_id)
    if not session.get('conversation_history'):
        raise HTTPException(status_code=404, detail="Session not found or empty")
    
    analytics = analytics_builder.build(session)
    return analytics


# =============================================================================
# WEBHOOK ENDPOINTS
# =============================================================================

class WebhookRegistration(BaseModel):
    url: str
    events: List[str] = ["scam_detected", "intel_extracted", "high_risk_profile"]
    secret: Optional[str] = None

@app.post("/webhook/register", response_model=WebhookConfig)
async def register_webhook(config: WebhookRegistration):
    """
    Register a webhook for real-time notifications
    Events: scam_detected, intel_extracted, high_risk_profile
    """
    webhook = webhook_manager.register(
        url=config.url,
        events=config.events,
        secret=config.secret
    )
    return webhook


@app.get("/webhook/list")
async def list_webhooks():
    """List all registered webhooks"""
    return {"webhooks": [w.model_dump() for w in webhook_manager.list_webhooks()]}


@app.delete("/webhook/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Unregister a webhook"""
    success = webhook_manager.unregister(webhook_id)
    if not success:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"status": "deleted", "webhook_id": webhook_id}


# =============================================================================
# SCAMMER PROFILING ENDPOINTS
# =============================================================================

@app.get("/profile/lookup")
async def lookup_profile(
    upi: Optional[str] = None,
    phone: Optional[str] = None,
    account: Optional[str] = None
):
    """
    Look up scammer profile by identifier
    Returns matching profile if found
    """
    intelligence = {
        'upi_ids': [{'upi_id': upi}] if upi else [],
        'phone_numbers': [phone] if phone else [],
        'bank_accounts': [{'account_number': account}] if account else []
    }
    
    match = scammer_profiler.lookup(intelligence)
    return match.model_dump()


@app.get("/profile/{profile_id}", response_model=ScammerProfile)
async def get_profile(profile_id: str):
    """Get scammer profile by ID"""
    profile = scammer_profiler.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.get("/profiles")
async def list_profiles(limit: int = 50, min_risk: float = 0.0):
    """List all scammer profiles, optionally filtered by risk score"""
    profiles = scammer_profiler.get_all_profiles()
    filtered = [p for p in profiles if p.risk_score >= min_risk]
    sorted_profiles = sorted(filtered, key=lambda p: p.risk_score, reverse=True)[:limit]
    return {
        "total": len(profiles),
        "filtered": len(sorted_profiles),
        "profiles": [p.model_dump() for p in sorted_profiles]
    }


# =============================================================================
# STARTUP/SHUTDOWN
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    logger.info("Starting Anti-Scam Sentinel API v2.0...")
    await session_manager.initialize()
    logger.info("✓ Session manager initialized")
    logger.info("✓ Scammer profiler initialized")
    logger.info("✓ Webhook manager initialized")
    logger.info("✓ All systems operational")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown"""
    logger.info("Shutting down Anti-Scam Sentinel API...")
    await session_manager.cleanup()
    logger.info("✓ Cleanup complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

