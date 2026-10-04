# Opportune AI — Phase 5G: Opportunity Quality & Verification

This patch builds on the current Phase 5 A→F version.

## What it fixes

- Separates actionable opportunities from collection/list pages and informational leads.
- Uses application/deadline context instead of arbitrary future dates when checking freshness.
- Rejects historical/expired application pages from the normal result list.
- Stops search snippets from being presented as verified funding/deadline facts.
- Labels search results as current candidates until the actual source page is fetched.
- Prioritizes official university/government/organization sources.
- If a Scholarship/Master's/Research search has fewer than five direct opportunities, it can expand up to two collection pages into individual same-domain opportunity links.
- Marks a fetched page as verified when the user chooses **Analyze & Prepare**.
- Improves result-card labels: View source, current candidate, source tier, and verification state.

## Apply

Extract this patch over the existing `D:\Opportune AI` project and replace the files when prompted.

Do not replace:

- `.env`
- `opportune.db`
- `uploads/`
- your existing `README.md`

Then restart Streamlit:

```bat
Ctrl+C
cd /d "D:\Opportune AI"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Expected behavior

A page such as `16 Master's Scholarships...` is treated as a collection, not as one scholarship. When direct results are scarce, Opportune can inspect a small number of collection pages and extract individual same-domain links.

A page with an old deadline such as 2023/2024/2025 is excluded unless the source provides an explicit current/rolling application signal.

Search-result snippets are discovery evidence, not final proof. Deep fields such as funding and tuition should be verified when **Analyze & Prepare** fetches the source page.
