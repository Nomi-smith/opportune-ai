from documents.cv_intelligence import (
    compare_cv_to_opportunity,
    extract_cv_signals,
)


class DocumentAgent:
    def analyze_cv(self, text: str) -> dict:
        return extract_cv_signals(text)

    def compare_cv(self, text: str, opportunity) -> dict:
        return compare_cv_to_opportunity(
            text,
            opportunity,
        )
