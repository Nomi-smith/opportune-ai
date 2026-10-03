from intelligence.agent_intelligence import analyze_opportunity


class IntelligenceAgent:
    def analyze(self, profile: dict, opportunity) -> dict:
        return analyze_opportunity(profile, opportunity)
