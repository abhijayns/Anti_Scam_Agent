from agent.detector import ScamDetector

class AntiScamAgent:
    def __init__(self):
        self.detector = ScamDetector()

    async def analyze(self, text: str):
        """
        Analyze the input text for potential scams.
        """
        result = await self.detector.detect(text)
        return result