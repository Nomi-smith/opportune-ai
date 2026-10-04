# Opportune AI — Final Discovery Consolidation

This is the **single consolidation patch** for the current discovery problems.

## What it fixes
1. Adds real Gemini Google Search grounding to discovery.
2. Adds an opportunity-specific Google Search Agent for Scholarship, Master's, Research, Internship and Job searches.
3. Automatically attaches the Google-grounded source to SourceManager.
4. Uses the supplied 597-entry scholarship/study source library as search targets.
5. Keeps source-page fetching/verification after Google discovery.
6. Fixes `1 June 2026` style deadline parsing.
7. Explicit `Status Closed` / closed markers override generic future-year text.
8. Adds Serper as an optional direct-Google fallback if `SERPER_API_KEY` is configured.
9. Keeps LLMs as planners/reviewers rather than inventing opportunity facts.

## Expected flow

USER FILTERS
→ opportunity-specific agent
→ live Google Search
→ 15–20 candidate URLs per lane
→ actual page fetch
→ type/country/level/currentness filters
→ deduplication
→ LLM quality review (if configured)
→ 10 per UI page, up to the accepted pool

An empty country means **global discovery**.

A catalogue/source page is a discovery source, not automatically a scholarship result.

## Important
The 597 scholarship entries are **source targets**, not pre-accepted live scholarships. The app still verifies live pages before showing an opportunity.

## Apply
Copy the files from this patch over the matching project paths. Keep your existing project files that are not in this patch.

Add `SERPER_API_KEY` only if you have one. Gemini Google Search grounding works from `GEMINI_API_KEY`.
