import json
import re

from database.db import list_applications, list_documents, load_profile
from intelligence.skill_taxonomy import extract_skills
from llm.manager import LLMManager
from core.actions import execute_action
from core.session import user_id

SYSTEM_PROMPT = '''You are Opportune AI, an expert personal opportunity and application intelligence agent.

Your expertise covers:
- jobs and internships: role fit, technical requirements, experience, location and application details
- master's/admissions: degree requirements, academic fit, language/standardized tests, deadlines, documents and funding
- scholarships: eligibility, funding, country/program restrictions and required evidence
- research positions/professors: research-topic fit, publications, skills, labs and outreach preparation
- CV/profile intelligence: evidence-based skills, projects, education, experience and document consistency
- application preparation: tailored CV guidance, cover letters, outreach messages, interview preparation and application roadmaps

Rules:
1. Treat the user's profile and uploaded documents as evidence. Never invent a skill, degree, score, project, employer, publication or credential.
2. Distinguish VERIFIED/PROFILE evidence from inferred or missing information.
3. If information is missing, ask the smallest useful follow-up question instead of guessing.
4. When discussing an opportunity, explain requirements, matched evidence, missing evidence, eligibility uncertainty, cost/funding and next steps when available.
5. Do not claim an opportunity is verified unless the source evidence supports it.
6. Never submit an application, bypass CAPTCHA/MFA, or request/store passwords.
7. When the user explicitly asks to change saved data, return ONLY JSON in this exact shape:
{"action":"ACTION_NAME","args":{...}}
Supported actions: update_profile, add_skills, remove_skills, remove_document, update_application, add_application, remove_application.
8. For a normal question, answer as an expert using the supplied context. Do not output action JSON.
9. Be practical and specific. Explain why something matches or does not match rather than giving a shallow generic answer.'''


def _context() -> str:
    try:
        profile = json.loads(load_profile(user_id()))
    except Exception:
        profile = {}
    docs = list_documents(user_id())
    apps = list_applications(user_id())
    safe_profile = {
        'full_name': profile.get('full_name', ''),
        'country': profile.get('country', ''),
        'city': profile.get('city', ''),
        'education': profile.get('education', []) or profile.get('education_text', ''),
        'skills': profile.get('skills', []),
        'career_interests': profile.get('career_interests', []),
        'study_interests': profile.get('study_interests', []),
        'research_interests': profile.get('research_interests', []),
        'experience': profile.get('experience', ''),
        'projects': profile.get('projects', []),
        'preferred_countries': profile.get('preferred_countries', []),
        'budget': profile.get('budget', ''),
        'tests': profile.get('tests', []),
    }
    doc_summary = [{'id': row['id'], 'filename': row['filename'], 'type': row['document_type']} for row in docs]
    app_summary = [{'id': row['id'], 'title': row['title'], 'organization': row['organization'], 'status': row['status'], 'deadline': row['deadline']} for row in apps[:30]]
    return json.dumps({'profile': safe_profile, 'documents': doc_summary, 'applications': app_summary}, ensure_ascii=False)


class ChatAgent:
    async def respond(self, prompt: str) -> tuple[str, bool]:
        grounded_prompt = f'''USER REQUEST:\n{prompt}\n\nCURRENT OPPORTUNE AI DATA:\n{_context()}\n\nUse this data as the source of truth for personal facts. If the user asks about their skills, projects, tests, documents, applications or profile, refer to the supplied data.'''
        raw = await LLMManager().generate(grounded_prompt, SYSTEM_PROMPT)
        match = re.search(r'\{\s*"action"\s*:\s*"[^"]+".*?\}', raw, re.S)
        if match:
            try:
                payload = json.loads(match.group(0))
                result = execute_action(payload['action'], payload.get('args', {}))
                return result, True
            except Exception:
                pass
        return raw, False
