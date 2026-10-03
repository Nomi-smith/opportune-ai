# Opportune AI — Gemini 3.8 / Google Search Fix

The previous build was calling `gemini-2.5-flash`. New Gemini API projects/users can be restricted from that model. This patch changes the LLM and Google Search grounding source to `gemini-3.8-flash`.

Google Search grounding remains implemented through Gemini's official `google_search` tool, and grounded URLs are fetched for opportunity extraction.

Apply these files over the existing project. Do not replace `.env` or `opportune.db`.

Restart Streamlit after copying the files.
