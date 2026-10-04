# Opportune AI — Phase 5H Global Multi-Source Discovery

This rebuild changes discovery from a small Google-like search into a global multi-source candidate collection pipeline.

## What changed
- Global source registry for study, scholarship, research, jobs and internships.
- Country-specific sources remain first-class, but global sources and major platforms are always searched too.
- Source-targeted search lanes explicitly include important portals such as DAAD, Erasmus+, EURAXESS, LinkedIn, Indeed, StepStone and other configured sources.
- Broad web discovery remains enabled for coverage.
- Candidate pool is expanded before filtering; up to 120 candidates are source-page verified, with up to 50 accepted results returned.
- Verification is concurrent with a bounded semaphore for speed.
- The requested country is never written into the opportunity's country field. Actual source content must support the destination.
- Actual source pages are required for accepted results.
- Discussion/forum/article/listicle pages are filtered out.
- Wrong study level is filtered out.
- Search provider names are not shown in result cards.
- Pagination remains 10 results per page without rerunning the search.

## Preserve
Do not replace `.env`, `opportune.db`, `uploads/`, `.git/`, or `.venv/`.
