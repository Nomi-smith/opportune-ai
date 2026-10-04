import streamlit as st
from config.settings import APPLICATION_STATUSES
from database.db import list_applications, save_application, update_application_status, delete_application
from core.session import user_id

def render():
    st.header('📌 Applications')
    results=st.session_state.get('search_results',[])
    if results:
        st.subheader('Save a discovered opportunity')
        titles=[x.get('title','Untitled') for x in results]
        selected=st.selectbox('Opportunity',titles,key='application_opportunity_select')
        item=next(x for x in results if x.get('title')==selected)
        if st.button('Save to Applications',key='save_discovery_application'):
            save_application(user_id(),{'opportunity_key':item.get('id') or item.get('application_url'),'title':item.get('title'),'organization':item.get('organization'),'status':'Saved','deadline':item.get('deadline'),'next_action':'Review official opportunity page'})
            st.success('Opportunity added to applications.')
    rows=list_applications(user_id())
    if not rows: st.info('No tracked applications yet.'); return
    st.divider()
    for row in rows:
        with st.container(border=True):
            st.subheader(row['title']); st.write(f"**Organization:** {row['organization']}")
            status=st.selectbox('Status',APPLICATION_STATUSES,index=APPLICATION_STATUSES.index(row['status']) if row['status'] in APPLICATION_STATUSES else 0,key=f'status_{row["id"]}')
            c1,c2=st.columns(2)
            with c1:
                if st.button('Update',key=f'update_{row["id"]}',use_container_width=True): update_application_status(row['id'],status); st.rerun()
            with c2:
                if st.button('🗑️ Remove',key=f'remove_application_{row["id"]}',use_container_width=True):
                    delete_application(row['id'],1); st.rerun()
            if row['deadline']: st.write(f"**Deadline:** {row['deadline']}")
            st.write(f"**Next action:** {row['next_action'] or 'Review requirements'}")
