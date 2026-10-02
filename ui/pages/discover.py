import asyncio

import streamlit as st

from intelligence.deduplication import (
    deduplicate_opportunities,
)
from intelligence.normalization import (
    normalize_results,
)
from models.opportunity import Opportunity
from sources.base import BaseSource
from sources.manager import SourceManager


class DemoSource(BaseSource):

    name = "Demo Source"

    async def search(
        self,
        query: str,
        opportunity_type: str | None = None,
        country: str | None = None,
    ) -> list[Opportunity]:

        # Temporary test data.
        # Real sources will be added in the next phase.

        return [
            Opportunity(
                title=f"{query.title()} Opportunity",
                organization="Example Organization",
                opportunity_type=(
                    opportunity_type
                    if opportunity_type
                    and opportunity_type != "All"
                    else "Internship"
                ),
                country=country or "Germany",
                description=(
                    "Temporary demonstration opportunity. "
                    "Real sources will replace this data."
                ),
                source_name=self.name,
                source_url="https://example.com",
                application_url="https://example.com",
                verification_status="UNVERIFIED",
            )
        ]


def search_opportunities(
    query: str,
    opportunity_type: str,
    country: str,
) -> list[Opportunity]:

    manager = SourceManager()

    # Temporary source used only to test the architecture.
    manager.register(DemoSource())

    results = asyncio.run(
        manager.search(
            query=query,
            opportunity_type=opportunity_type,
            country=country or None,
        )
    )

    results = normalize_results(results)

    results = deduplicate_opportunities(results)

    return results


def render():

    st.header("Discover Opportunities")

    st.write(
        "Search across multiple opportunity sources."
    )

    opportunity_type = st.selectbox(
        "Opportunity type",
        [
            "All",
            "Job",
            "Internship",
            "Master's",
            "Scholarship",
            "Research",
        ],
    )

    query = st.text_input(
        "What are you looking for?",
        placeholder=(
            "e.g. Fully funded AI master's in Europe"
        ),
    )

    country = st.text_input(
        "Preferred country",
        placeholder="e.g. Germany",
    )

    if st.button(
        "Search Opportunities",
        type="primary",
    ):

        if not query.strip():

            st.warning(
                "Please enter what you're looking for."
            )

            return

        with st.spinner(
            "Searching opportunity sources..."
        ):

            try:

                results = search_opportunities(
                    query=query,
                    opportunity_type=opportunity_type,
                    country=country,
                )

                st.session_state.search_results = [
                    item.model_dump()
                    for item in results
                ]

            except Exception as exc:

                st.error(
                    f"Search failed: {exc}"
                )

    results = st.session_state.search_results

    if results:

        st.divider()

        st.subheader(
            f"Found {len(results)} opportunity(s)"
        )

        for item in results:

            with st.container(border=True):

                st.subheader(
                    item["title"]
                )

                st.write(
                    f"**Organization:** "
                    f"{item['organization']}"
                )

                st.write(
                    f"**Type:** "
                    f"{item['opportunity_type']}"
                )

                if item.get("country"):
                    st.write(
                        f"**Country:** "
                        f"{item['country']}"
                    )

                st.write(
                    f"**Verification:** "
                    f"{item['verification_status']}"
                )

                if item.get("description"):
                    st.write(
                        item["description"]
                    )

                if item.get(
                    "application_url"
                ):
                    st.link_button(
                        "Application Link",
                        item["application_url"],
                    )

    else:

        st.info(
            "No opportunities found yet. "
            "Real discovery sources will be connected next."
        )