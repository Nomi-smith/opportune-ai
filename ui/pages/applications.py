from database.db import delete_application
import streamlit as st

from config.settings import APPLICATION_STATUSES
from database.db import (
    list_applications,
    save_application,
    update_application_status,
)

def render():
    st.header("📌 Applications")

    if st.session_state.search_results:
        st.subheader("Save a discovered opportunity")

        titles = [
            item["title"]
            for item in st.session_state.search_results
        ]

        selected = st.selectbox("Opportunity", titles)

        item = next(
            x for x in st.session_state.search_results
            if x["title"] == selected
        )

        if st.button("Save to Applications"):
            save_application(
                1,
                {
                    "opportunity_key": item.get("id") or item.get("application_url"),
                    "title": item["title"],
                    "organization": item["organization"],
                    "status": "Saved",
                    "deadline": item.get("deadline"),
                    "next_action": "Review official opportunity page",
                },
            )
            st.success("Opportunity added to applications.")

    rows = list_applications(1)

    if not rows:
        st.info("No tracked applications yet.")
        return

    st.divider()

    for row in rows:
        with st.container(border=True):
            st.subheader(row["title"])
            st.write(f"**Organization:** {row['organization']}")

            status = st.selectbox(
                "Status",
                APPLICATION_STATUSES,
                index=(
                    APPLICATION_STATUSES.index(row["status"])
                    if row["status"] in APPLICATION_STATUSES
                    else 0
                ),
                key=f"status_{row['id']}",
            )

            b1, b2 = st.columns(2)
            with b1:
                if st.button("Update", key=f"update_{row['id']}"):
                    update_application_status(row["id"], status)
                    st.rerun()
            with b2:
                if st.button("🗑️ Remove", key=f"remove_{row['id']}"):
                    delete_application(row["id"], 1)
                    st.rerun()

            if row["deadline"]:
                st.write(f"**Deadline:** {row['deadline']}")

            st.write(
                f"**Next action:** "
                f"{row['next_action'] or 'Review requirements'}"
            )
