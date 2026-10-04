# Opportune AI — Phase 5G.2 Discovery Quality Rebuild

This patch rebuilds discovery as one coherent pipeline:

- Separate Study / Degree from Scholarship, Research, Job and Internship.
- Add Bachelor's / Master's / PhD study-level selection.
- Add Research level selection.
- Treat destination country as a hard filter.
- Search each selected country independently instead of mixing countries into one query.
- Prioritize country-specific preferred sources while keeping global discovery available.
- Fetch actual source pages before accepting candidates.
- Reject wrong degree levels, wrong countries, discussions/articles and non-actionable pages.
- Treat deadline/funding as explicit source-page facts; unavailable facts remain N/A.
- Do not use a year mention alone as proof that an opportunity is open.
- Hide search-provider names such as Serper from result cards.
- Keep source diagnostics only under the developer diagnostics expander.
- Keep collection pages as fallback inputs only; expanded links pass the same filters.

Replace the matching files over the existing project. Preserve `.env`, `opportune.db`, `uploads/`, and all other project files.
