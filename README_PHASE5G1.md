# Opportune AI — Phase 5G.1

## Stable Current Discovery + Country-Aware Source Priority

This patch fixes two issues from Phase 5G:

1. `NameError: availability_reason is not defined` in `discovery_planner.py`.
2. Discovery now uses a **country-aware source strategy**: preferred official/national/major portals are searched first and ranked ahead of the broad web, while broad discovery remains available.

### Country-aware discovery

For a selected country and opportunity type, the planner builds three parallel search lanes:

1. **Preferred-source lane** — uses country-specific `site:` hints for authoritative/national portals.
2. **Trusted/major-source lane** — combines the same source registry with broader opportunity terminology.
3. **Broad-web lane** — searches the wider public web so the registry never becomes an exclusive allow-list.

Results from preferred domains receive a `country_source_priority=preferred` signal and are ranked ahead of generic web results.

The registry covers the countries currently offered by the UI, including Germany, Netherlands, Sweden, Denmark, Finland, Norway, France, Italy, Spain, Portugal, Austria, Switzerland, Belgium, UK, Ireland, Poland, Czech Republic, Hungary, Türkiye, Romania, Estonia, Latvia, Lithuania, Greece, United States, Canada, Australia, New Zealand, Japan, South Korea, China, Singapore, Malaysia, UAE, Saudi Arabia, Qatar, Pakistan, India, South Africa, and Brazil.

This is a **priority system, not a claim that one website is universally best**. Official/national sources are preferred where known; major academic/job portals are secondary; the open web remains a fallback.

### Preserve

Do not replace:

- `.env`
- `opportune.db`
- `uploads/`
- existing `README.md`

### Restart

```bat
Ctrl+C
cd /d "D:\Opportune AI"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### Test

Try:

- Scholarship → Machine Learning → Germany
- Master's → Artificial Intelligence → Denmark
- Job → any role → Germany

Check Search diagnostics and confirm preferred-source results are ranked before generic web results when available.
