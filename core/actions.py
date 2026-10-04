import json
from database.db import delete_document, load_profile, save_profile, update_application_status, save_application, delete_application
from intelligence.skill_taxonomy import merge_skills
from core.session import user_id


def _profile():
    try:
        return json.loads(load_profile(user_id()))
    except Exception:
        return {}


def update_profile_fields(fields: dict):
    profile = _profile()
    profile.update(fields or {})
    if 'skills' in profile:
        profile['skills'] = merge_skills(profile.get('skills', []))
    save_profile(user_id(), json.dumps(profile))
    return 'Profile updated successfully.'


def add_skills(skills: list[str]):
    profile = _profile()
    profile['skills'] = merge_skills(profile.get('skills', []), skills)
    save_profile(user_id(), json.dumps(profile))
    return 'Skills added/merged without duplicates.'


def remove_skills(skills: list[str]):
    remove = set(merge_skills(skills))
    profile = _profile()
    profile['skills'] = [x for x in merge_skills(profile.get('skills', [])) if x not in remove]
    save_profile(user_id(), json.dumps(profile))
    return 'Skills removed from the profile.'


def remove_document(document_id: int):
    path = delete_document(int(document_id), 1)
    if path:
        return 'Document removed.'
    return 'Document was not found.'


def update_application(application_id: int, status: str):
    update_application_status(int(application_id), status)
    return 'Application status updated.'

def add_application(title: str, organization: str, deadline: str = '', opportunity_key: str = '', next_action: str = 'Review official opportunity page'):
    save_application(user_id(), {'opportunity_key': opportunity_key, 'title': title, 'organization': organization, 'status': 'Saved', 'deadline': deadline, 'next_action': next_action})
    return 'Opportunity added to the application tracker.'

def remove_application(application_id: int):
    return 'Application removed.' if delete_application(int(application_id), 1) else 'Application was not found.'


ACTION_HANDLERS = {
    'update_profile': update_profile_fields,
    'add_skills': add_skills,
    'remove_skills': remove_skills,
    'remove_document': remove_document,
    'update_application': update_application,
    'add_application': add_application,
    'remove_application': remove_application,
}


def execute_action(action: str, args: dict | None = None) -> str:
    handler = ACTION_HANDLERS.get(action)
    if not handler:
        return f'Unknown action: {action}'
    return handler(**(args or {}))
