import random
from typing import Dict, List

class ScammerSimulator:
    """
    Mock Scammer API for simulating scammer behavior.
    Used for testing the autonomous honeypot agent.
    """
    
    SCAM_FLOWS = {
        "job_scam": [
            "Hi! We saw your profile and you are selected for a part-time job. 5000/day. Interested?",
            "Great! You just need to like some YouTube videos. First, tell me your Telegram username.",
            "Okay. To start, you need to pay a small security deposit of Rs 500. Pay to this UPI: workhr@paytm",
            "Confirmed. Now for the high-paying tasks, we need your bank details to credit salary. Share Account No and IFSC.",
            "Account: 9988776655, IFSC: HDFC0001234. Please send verification screenshot."
        ],
        "bank_fraud": [
            "URGENT: Your SBI account is blocked due to suspicious activity. Verify now: http://sbi-secure-kyc.com",
            "You must update your KYC immediately or your card will be cancelled.",
            "Please provide your customer ID and the OTP you just received.",
            "To reactivate, transfer Rs 1 to this virtual account: helpdesk@oksbi",
            "Thank you. Our executive will call you."
        ],
        "lottery_scam": [
            "CONGRATULATIONS! You have won Rs 25,00,000 in KBC Lottery! Contact Mr. Khanna at 9876543210",
            "To claim your prize, you need to pay processing fee of Rs 12,500.",
            "Pay fee to: winner-claims@icici. Account No: 1122334455, IFSC: ICIC0000001",
            "Lottery file is processing. Send Rs 5000 more for GST."
        ]
    }

    def __init__(self, scam_type: str = None):
        if not scam_type:
            scam_type = random.choice(list(self.SCAM_FLOWS.keys()))
        self.scam_type = scam_type
        self.step = 0

    def generate_message(self, last_agent_message: str = None) -> str:
        """
        Generate the next scammer message in the flow.
        Slowly reveals bank details/UPI IDs.
        """
        flow = self.SCAM_FLOWS.get(self.scam_type, self.SCAM_FLOWS["job_scam"])
        
        if self.step < len(flow):
            message = flow[self.step]
            self.step += 1
            return message
        else:
            return "Why are you taking so long? Just pay the amount immediately!"

def simulate_scammer_turn(scam_type: str, step: int) -> str:
    """Helper for stateless simulation"""
    flow = ScammerSimulator.SCAM_FLOWS.get(scam_type, ScammerSimulator.SCAM_FLOWS["job_scam"])
    if step < len(flow):
        return flow[step]
    return "I'm waiting! Send the details now."
