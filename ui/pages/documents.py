from pathlib import Path
import streamlit as st
from config.settings import UPLOAD_DIR
from database.db import delete_document, list_documents, load_profile, save_document, save_profile
from documents.cv_intelligence import extract_cv_signals
from documents.extract import extract_text
from intelligence.profile_intelligence import merge_document_into_profile


def render():
    st.header('📄 Documents')
    uploaded = st.file_uploader('Upload CV, transcript, certificate, SOP draft, or similar', type=['pdf', 'docx', 'txt', 'md'])
    doc_type = st.selectbox('Document type', ['Master CV', 'Transcript', 'Degree', 'Certificate', 'Language Test', 'Recommendation', 'Other'])

    if uploaded and st.button('Add / Replace Document', type='primary'):
        safe_name = Path(uploaded.name).name
        path = UPLOAD_DIR / safe_name
        path.write_bytes(uploaded.getbuffer())
        try:
            text = extract_text(str(path))
        except Exception:
            text = ''
        save_document(1, safe_name, doc_type, str(path), text)

        # Every uploaded document may add evidence, but only unique/canonical facts are merged.
        if text:
            current = __import__('json').loads(load_profile(1))
            updated = merge_document_into_profile(text, current, f'{doc_type}: {safe_name}')
            save_profile(1, __import__('json').dumps(updated))

        st.success(f'Saved {safe_name}. New information was merged without duplicate skills.')
        st.rerun()

    rows = list_documents(1)
    if not rows:
        st.info('No documents uploaded yet.')
        return

    st.divider()
    st.subheader('Saved documents')
    for row in rows:
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.write(f"**{row['filename']}** — {row['document_type']}")
            with c2:
                if st.button('Remove', key=f"remove_doc_{row['id']}"):
                    old_path = delete_document(row['id'], 1)
                    if old_path:
                        try:
                            Path(old_path).unlink(missing_ok=True)
                        except Exception:
                            pass
                    st.rerun()
            if row['extracted_text']:
                with st.expander('Extracted text preview'):
                    st.text(row['extracted_text'][:3000])
            if row['document_type'] == 'Master CV' and row['extracted_text']:
                signals = extract_cv_signals(row['extracted_text'])
                st.caption('Indexed skills: ' + (', '.join(signals['skills']) if signals['skills'] else 'None'))

    st.caption('Removing a document removes the uploaded file and document record. Profile facts already saved remain, so deleting a file never silently destroys your profile.')
