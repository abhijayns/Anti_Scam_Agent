from typing import Dict, Optional
import logging
from agent.detector import ScamDetector
from agent.orchestrator import ConversationOrchestrator
from agent.extractor import IntelligenceExtractor
from agent.session_manager import SessionManager

logger = logging.getLogger(__name__)

class AntiScamAgent:
    def __init__(self):
        self.detector = ScamDetector()
        self.orchestrator = ConversationOrchestrator()
        self.extractor = IntelligenceExtractor()
        self.session_manager = SessionManager()
        self._initialized = False

    async def initialize(self):
        if not self._initialized:
            await self.session_manager.initialize()
            self._initialized = True

    async def analyze(self, text: str, session_id: str = "default"):
        """
        Legacy analyze method - simplified detection only.
        """
        result = await self.detector.detect(text)
        return result

    async def engage(self, session_id: str, message: str) -> Dict:
        """
        Autonomous engagement: Detect -> Orchestrate -> Extract -> Respond
        Returns a structured JSON with the full state.
        """
        if not self._initialized:
            await self.initialize()

        # 1. Load session
        session = await self.session_manager.load_session(session_id)
        
        # 2. Detect scam
        detection_result = await self.detector.detect(message, session.get('conversation_history', []))
        
        # 3. Extract intelligence
        intelligence = await self.extractor.extract_intelligence(message, session)
        
        # 4. Generate orchestrated response
        # Update session with scammer message first
        session.setdefault('conversation_history', []).append({
            'role': 'scammer',
            'message': message
        })
        
        agent_response_data = await self.orchestrator.generate_response(session, detection_result)
        
        # 5. Update session state
        updated_session = self.orchestrator.update_session_state(
            session, 
            intelligence, 
            agent_response_data
        )
        await self.session_manager.save_session(updated_session)
        
        # 6. Return structured JSON
        return {
            "session_id": session_id,
            "is_scam": detection_result.is_scam,
            "confidence_score": detection_result.confidence_score,
            "agent_response": agent_response_data.get('message', ''),
            "scam_type": detection_result.scam_type,
            "extracted_intelligence": updated_session['intelligence'],
            "phase": str(updated_session['current_phase'])
        }