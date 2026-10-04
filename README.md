# Phase 5G.1 Freshness Fix

Fixes the `NameError: ACTION_PATTERNS is not defined` crash in `intelligence/freshness.py` by importing the shared action-pattern constants from `intelligence.opportunity_quality`.

Replace the existing `intelligence/freshness.py` with the included file. No database, `.env`, or other project files need to be changed.
