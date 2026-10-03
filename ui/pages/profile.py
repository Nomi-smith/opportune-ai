import json
import asyncio
from pathlib import Path

import streamlit as st

from config.settings import UPLOAD_DIR
from database.db import delete_document, list_documents, load_profile, save_document, save_profile
from documents.extract import extract_text
from documents.cv_intelligence import extract_cv_signals
from intelligence.profile_intelligence import build_profile_from_cv, build_profile_from_cv_with_llm
from llm.manager import LLMManager


def _csv(value):
    return [item.strip() for item in value.split(',') if item.strip()]


def _dedupe_dicts(items, key_fields):
    result, seen = [], set()
    for item in items or []:
        if not isinstance(item, dict):
            continue
        key = tuple(str(item.get(k, '')).strip().casefold() for k in key_fields)
        if not any(key) or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _normalize_projects(projects):
    normalized = []
    if isinstance(projects, str):
        text = projects.strip()
        return [{'title': '', 'description': text}] if text else []
    for item in projects or []:
        if isinstance(item, str):
            text = item.strip()
            if text:
                normalized.append({'title': text[:120], 'description': text})
        elif isinstance(item, dict):
            title = str(item.get('title', '') or '').strip()
            description = str(item.get('description', '') or '').strip()
            if title or description:
                normalized.append({'title': title, 'description': description})
    return _dedupe_dicts(normalized, ('title', 'description'))


def _clean_obvious_cv_project_clutter(projects):
    """Remove only unmistakable CV section headings/coursework accidentally stored as projects."""
    bad_exact = {
        'relevant coursework', 'coursework', 'freelance experience', 'leadership',
        'leadership experience', 'professional experience', 'work experience',
        'experience', 'skills', 'technical skills', 'education', 'certifications',
    }
    cleaned = []
    for item in _normalize_projects(projects):
        title = item['title'].strip()
        low = title.casefold()
        desc = item['description'].strip()
        if low in bad_exact:
            continue
        if low.startswith('project from cv'):
            # This was the old fallback label used when a CV parser could not find a project boundary.
            # Do not keep it as a fake project.
            continue
        if '•' in title and low.startswith(('algorithms', 'database systems', 'software engineering')):
            continue
        cleaned.append(item)
    return cleaned


def _init_project_state(projects):
    if 'profile_projects' not in st.session_state:
        st.session_state.profile_projects = _clean_obvious_cv_project_clutter(projects)


def _init_tests_state(tests):
    if 'profile_tests' not in st.session_state:
        st.session_state.profile_tests = [
            {
                'name': item.get('name', ''),
                'has_result': bool(item.get('has_result', False)),
                'score': item.get('score', ''),
                'details': item.get('details', ''),
                'document_id': item.get('document_id'),
            }
            for item in (tests or []) if isinstance(item, dict)
        ]


def _sync_projects_from_widgets():
    """Sync visible project widgets without dropping blank blocks.

    Blank blocks must be preserved so Add/Remove changes exactly one project.
    Normalization/deduplication is intentionally deferred to Save Profile.
    """
    projects = []
    for i in range(len(st.session_state.get('profile_projects', []))):
        title = str(st.session_state.get(f'project_title_{i}', '') or '').strip()
        desc = str(st.session_state.get(f'project_desc_{i}', '') or '').strip()
        projects.append({'title': title, 'description': desc})
    st.session_state.profile_projects = projects


def _add_project():
    _sync_projects_from_widgets()
    st.session_state.profile_projects.append({'title': '', 'description': ''})
    st.rerun()


def _remove_last_project():
    _sync_projects_from_widgets()
    if st.session_state.profile_projects:
        st.session_state.profile_projects.pop()
    st.rerun()


def _save_profile(data, fields):
    _sync_projects_from_widgets()
    projects = _normalize_projects(
        [p for p in st.session_state.profile_projects if p.get('title') or p.get('description')]
    )
    tests = []
    for i in range(len(st.session_state.get('profile_tests', []))):
        name_i = str(st.session_state.get(f'test_name_{i}', '') or '').strip()
        if not name_i:
            continue
        has_result = st.session_state.get(f'test_result_{i}', 'No') == 'Yes'
        tests.append({
            'name': name_i,
            'has_result': has_result,
            'score': str(st.session_state.get(f'test_score_{i}', '') or '').strip() if has_result else '',
            'details': str(st.session_state.get(f'test_details_{i}', '') or '').strip() if has_result else '',
        })
    payload = dict(data)
    payload.update({
        'full_name': fields['name'].strip(), 'email': fields['email'].strip(),
        'country': fields['country'].strip(), 'city': fields['city'].strip(),
        'skills': _csv(fields['skills']), 'career_interests': _csv(fields['career']),
        'study_interests': _csv(fields['study']), 'research_interests': _csv(fields['research']),
        'preferred_countries': _csv(fields['preferred_countries']), 'experience': fields['experience'],
        'projects': projects, 'education_text': fields['education_text'],
        'education': [{'raw': fields['education_text']}] if fields['education_text'].strip() else data.get('education', []),
        'budget': fields['budget'], 'tests': _dedupe_dicts(tests, ('name', 'score', 'details')),
    })
    save_profile(1, json.dumps(payload))
    st.session_state.profile_projects = projects


def render():
    st.header('👤 My Profile')
    try:
        data = json.loads(load_profile(1))
    except Exception:
        data = {}

    _init_project_state(data.get('projects', []))
    _init_tests_state(data.get('tests', []))

    # IMPORTANT: Profile inputs are deliberately NOT inside one giant st.form.
    # Streamlit forms batch widget state, which made the old Add Project interaction
    # unreliable. Normal widgets update session state immediately, so Add Project
    # can safely append a block without losing what the user has typed.
    name = st.text_input('Full name', data.get('full_name', ''), key='profile_name')
    email = st.text_input('Email', data.get('email', ''), key='profile_email')
    country = st.text_input('Current country', data.get('country', ''), key='profile_country')
    city = st.text_input('Current city', data.get('city', ''), key='profile_city')
    skills = st.text_area('Skills (comma separated)', ', '.join(data.get('skills', [])), key='profile_skills')
    career = st.text_area('Career interests (comma separated)', ', '.join(data.get('career_interests', [])), key='profile_career')
    study = st.text_area('Study interests (comma separated)', ', '.join(data.get('study_interests', [])), key='profile_study')
    research = st.text_area('Research interests (comma separated)', ', '.join(data.get('research_interests', [])), key='profile_research')
    preferred_countries = st.text_area('Preferred countries (comma separated)', ', '.join(data.get('preferred_countries', [])), key='profile_preferred_countries')
    experience = st.text_area('Experience', data.get('experience', ''), key='profile_experience')
    education_text = st.text_area('Education', data.get('education_text', ''), placeholder='e.g. BS Computer Science (Artificial Intelligence), AWKUM, CGPA 3.45/4.00', key='profile_education')
    budget = st.text_input('Budget', data.get('budget', ''), key='profile_budget')

    st.subheader('🚀 Projects')
    st.caption('Projects are manual evidence blocks. CV parsing will not automatically create projects. Add projects yourself; LLM-based extraction can be enabled later.')

    project_controls = st.columns(3)
    with project_controls[0]:
        if st.button('➕ Add Project', key='add_project_btn', use_container_width=True):
            _add_project()
    with project_controls[1]:
        if st.button('🗑 Remove Last Project', key='remove_project_btn', use_container_width=True):
            _remove_last_project()
    with project_controls[2]:
        if st.button('🧹 Clean obvious CV clutter', key='clean_project_btn', use_container_width=True):
            _sync_projects_from_widgets()
            st.session_state.profile_projects = _clean_obvious_cv_project_clutter(st.session_state.profile_projects)
            st.success('Obvious CV section headings/coursework labels were removed. Real project entries were kept.')
            st.rerun()

    for i, project in enumerate(st.session_state.profile_projects):
        st.markdown(f'**Project {i + 1}**')
        st.text_input('Project name', project.get('title', ''), key=f'project_title_{i}')
        st.text_area('What did you build/do?', project.get('description', ''), key=f'project_desc_{i}', height=120)

    st.subheader('🌐 Language / Admission / Standardized Tests')
    st.caption('Add IELTS, TOEFL, PTE, GRE, GMAT, SAT, language certificates, or any other test a country/program may require.')
    for i, test in enumerate(st.session_state.profile_tests):
        st.markdown(f'**Test {i + 1}**')
        st.text_input('Test name', test.get('name', ''), key=f'test_name_{i}')
        has_result = st.radio('Have results?', ['No', 'Yes'], index=1 if test.get('has_result') else 0, horizontal=True, key=f'test_result_{i}')
        if has_result == 'Yes':
            st.text_input('Score / result', test.get('score', ''), key=f'test_score_{i}')
            st.text_input('Additional details (date, band breakdown, validity, etc.)', test.get('details', ''), key=f'test_details_{i}')
        else:
            st.caption('No result recorded yet. You can add/upload evidence later.')

    if st.button('💾 Save Profile', type='primary', key='save_profile_btn'):
        _save_profile(data, {
            'name': name, 'email': email, 'country': country, 'city': city,
            'skills': skills, 'career': career, 'study': study, 'research': research,
            'preferred_countries': preferred_countries, 'experience': experience,
            'education_text': education_text, 'budget': budget,
        })
        st.success('Profile saved permanently.')

    st.divider()
    st.subheader('📄 Master CV → Profile')
    st.caption('The CV is evidence. Detected facts are merged into your existing profile and duplicates are removed. Deterministic CV parsing does not create project blocks.')

    cv_uploaded = st.file_uploader('Upload or replace Master CV', type=['pdf', 'docx', 'txt', 'md'], key='profile_master_cv')
    if cv_uploaded and st.button('Extract CV into Profile', type='secondary', key='extract_cv_btn'):
        safe_name = Path(cv_uploaded.name).name
        path = UPLOAD_DIR / safe_name
        path.write_bytes(cv_uploaded.getbuffer())
        text = extract_text(str(path))
        if not text.strip():
            st.error('No readable text was extracted from this CV.')
            return
        save_document(1, safe_name, 'Master CV', str(path), text)
        current = json.loads(load_profile(1))
        updated = build_profile_from_cv(text, current)
        llm_manager = LLMManager()
        if llm_manager.has_external_provider:
            try:
                updated = asyncio.run(build_profile_from_cv_with_llm(text, updated))
                st.caption('LLM-assisted CV understanding was used; only facts explicitly supported by the CV were merged.')
            except Exception as exc:
                st.warning(f'LLM CV understanding was unavailable, so deterministic extraction was kept: {exc}')
        save_profile(1, json.dumps(updated))
        signals = extract_cv_signals(text)
        st.success('Master CV indexed and profile updated.')
        st.write('**Detected/merged skills:** ' + (', '.join(signals['skills']) if signals['skills'] else 'None'))
        # Reload project state from the saved profile without inventing projects.
        st.session_state.pop('profile_projects', None)
        st.rerun()

    st.divider()
    st.subheader('📚 Uploaded Documents')
    documents = list_documents(1)
    if not documents:
        st.caption('No uploaded documents yet.')
    else:
        for row in documents:
            c1, c2 = st.columns([5, 1])
            with c1:
                st.write(f"**{row['filename']}** — {row['document_type']}")
            with c2:
                if st.button('Remove', key=f"remove_doc_{row['id']}"):
                    path = delete_document(row['id'], 1)
                    if path:
                        try:
                            Path(path).unlink(missing_ok=True)
                        except Exception:
                            pass
                    st.rerun()

    sources = data.get('field_sources', {})
    if sources:
        with st.expander('Evidence / source tracking'):
            for field, source in sorted(sources.items()):
                st.write(f'- **{field}** → {source}')
