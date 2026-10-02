import asyncio

import streamlit as st

from intelligence.deduplication import deduplicate_opportunities
from intelligence.normalization import normalize_results
from sources.jobs.arbeitnow import ArbeitnowSource
from sources.manager import SourceManager


async def search_opportunities(query: str):
    manager = SourceManager(
        sources=[
            ArbeitnowSource(),
        ]
    )

    results = await manager.search(query=query)

    normalized = normalize_results(results)
    deduplicated = deduplicate_opportunities(normalized)

    return deduplicated


def render():
    st.header("🔎 Discover Opportunities")

    query = st.text_input(
        "What are you looking for?",
        placeholder="e.g. Python developer",
    )

    if st.button("Search") and query.strip():
        with st.spinner("Searching opportunities..."):
            results = asyncio.run(search_opportunities(query.strip()))

        if not results:
            st.info("No opportunities found.")
            return

        st.success(f"Found {len(results)} opportunities.")

        for opportunity in results:
            with st.container(border=True):
                st.subheader(opportunity.title)

                st.write(
                    f"**Organization:** {opportunity.organization}"
                )

                if opportunity.city:
                    st.write(f"**Location:** {opportunity.city}")

                if opportunity.source_name:
                    st.caption(
                        f"Source: {opportunity.source_name} • "
                        f"Status: {opportunity.verification_status}"
                    )

                if opportunity.application_url:
                    st.link_button(
                        "View Opportunity",
                        opportunity.application_url,
                    )