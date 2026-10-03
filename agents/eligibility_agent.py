from intelligence.eligibility import evaluate

class EligibilityAgent:
    def run(self, profile, opportunity):
        return evaluate(profile, opportunity)
