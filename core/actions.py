import json
from database.db import delete_document, delete_application, load_profile, save_profile, update_application_status
from intelligence.skill_taxonomy import merge_skills


def _profile():
    try:
        return json.loads(load_profile(1))
    except Exception:
        return {}


def update_profile_fields(fields: dict):
    profile = _profile()
    profile.update(fields or {})
    if 'skills' in profile:
        profile['skills'] = merge_skills(profile.get('skills', []))
    save_profile(1, json.dumps(profile))
    return 'Profile updated successfully.'


def add_skills(skills: list[str]):
    profile = _profile()
    profile['skills'] = merge_skills(profile.get('skills', []), skills)
    save_profile(1, json.dumps(profile))
    return 'Skills added/merged without duplicates.'


def remove_skills(skills: list[str]):
    remove = set(merge_skills(skills))
    profile = _profile()
    profile['skills'] = [x for x in merge_skills(profile.get('skills', [])) if x not in remove]
    save_profile(1, json.dumps(profile))
    return 'Skills removed from the profile.'


def remove_document(document_id: int):
    path = delete_document(int(document_id), 1)
    if path:
        return 'Document removed.'
    return 'Document was not found.'



def remove_application(application_id: int):
    return 'Application removed.' if delete_application(int(application_id), 1) else 'Application was not found.'

def update_application(application_id: int, status: str):
    update_application_status(int(application_id), status)
    return 'Application status updated.'


ACTION_HANDLERS = {
    'update_profile': update_profile_fields,
    'add_skills': add_skills,
    'remove_skills': remove_skills,
    'remove_document': remove_document,
    'update_application': update_application,
    'remove_application': remove_application,
}


def execute_action(action: str, args: dict | None = None) -> str:
    handler = ACTION_HANDLERS.get(action)
    if not handler:
        return f'Unknown action: {action}'
    return handler(**(args or {}))
