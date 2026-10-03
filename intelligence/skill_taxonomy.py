import re

SKILL_ALIASES = {
    "python": ["python", "python3"],
    "machine learning": ["machine learning", "machine-learning", "ml"],
    "deep learning": ["deep learning", "deep-learning"],
    "computer vision": ["computer vision", "computer-vision"],
    "natural language processing": ["natural language processing", "nlp", "natural-language-processing"],
    "generative ai": ["generative ai", "genai", "gen ai"],
    "llm": ["llm", "llms", "large language model", "large language models"],
    "ai agents": ["ai agents", "ai agent", "agentic ai", "agentic agents"],
    "rag": ["rag", "retrieval augmented generation", "retrieval-augmented generation"],
    "pytorch": ["pytorch", "torch"],
    "tensorflow": ["tensorflow", "tf"],
    "opencv": ["opencv", "open cv"],
    "yolo": ["yolo", "yolov8", "yolov9", "yolov10", "yolov11"],
    "sql": ["sql", "mysql", "postgresql", "postgres"],
    "git": ["git", "github", "gitlab"],
    "docker": ["docker", "docker compose"],
    "fastapi": ["fastapi"],
    "streamlit": ["streamlit"],
    "react": ["react", "reactjs", "react.js"],
    "next.js": ["next.js", "nextjs", "next js"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "transformers": ["transformers", "hugging face transformers"],
    "hugging face": ["hugging face", "huggingface"],
    "prompt engineering": ["prompt engineering", "prompt design"],
    "api development": ["api development", "rest api", "restful api"],
}


def normalize_text(text: str) -> str:
    return " ".join((text or "").lower().split())


def canonical_skill(skill: str) -> str:
    value = normalize_text(skill)
    if not value:
        return ""
    for canonical, aliases in SKILL_ALIASES.items():
        if value == canonical or value in {normalize_text(a) for a in aliases}:
            return canonical
    return value


def merge_skills(*skill_lists) -> list[str]:
    merged = []
    seen = set()
    for values in skill_lists:
        for item in values or []:
            canonical = canonical_skill(str(item))
            if not canonical or canonical in seen:
                continue
            seen.add(canonical)
            merged.append(canonical)
    return sorted(merged)


def extract_skills(text: str) -> list[str]:
    normalized = normalize_text(text)
    found = []
    for canonical, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            pattern = r"(?<![a-z0-9])" + re.escape(normalize_text(alias)).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
            if re.search(pattern, normalized):
                found.append(canonical)
                break
    return sorted(set(found))


def skill_aliases(skill: str) -> list[str]:
    canonical = canonical_skill(skill)
    return SKILL_ALIASES.get(canonical, [canonical])
