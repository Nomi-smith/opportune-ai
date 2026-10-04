import os
import re
import httpx
from llm.base import BaseLLM

class GeminiLLM(BaseLLM):
    name = "gemini"

    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    async def generate(self, prompt: str, system: str = "") -> str:
        models = []
        configured = os.getenv("GEMINI_MODEL", "").strip()
        for candidate in [configured, self.model, "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-2.5-flash"]:
            if candidate and candidate not in models:
                models.append(candidate)
        errors = []
        async with httpx.AsyncClient(timeout=60) as client:
            for model in models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                payload = {"contents": [{"parts": [{"text": f"{system}\n\n{prompt}"}]}]}
                try:
                    r = await client.post(url, params={"key": self.api_key}, json=payload)
                    if r.status_code >= 400:
                        errors.append(f"{model}: HTTP {r.status_code} {r.text[:250]}")
                        continue
                    data = r.json()
                    candidates = data.get("candidates") or []
                    if not candidates:
                        errors.append(f"{model}: no candidates"); continue
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = "".join(str(p.get("text","")) for p in parts).strip()
                    if text:
                        self.model = model
                        return text
                    errors.append(f"{model}: empty response")
                except Exception as exc:
                    errors.append(f"{model}: {exc}")
        raise RuntimeError("Gemini failed: " + " | ".join(errors)[-1600:])

    async def search_web(self, prompt: str, max_results: int = 20) -> list[dict]:
        """Use Gemini's real Google Search grounding and return the grounded web sources.

        Gemini performs the Google queries itself; we only turn its grounding chunks into
        candidate URLs. Those URLs are fetched and verified by Opportune's normal pipeline.
        """
        models = []
        configured = os.getenv("GEMINI_MODEL", "").strip()
        for candidate in [configured, self.model, "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-2.5-flash"]:
            if candidate and candidate not in models:
                models.append(candidate)
        errors=[]
        async with httpx.AsyncClient(timeout=75) as client:
            for model in models:
                url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                payload={
                    "contents":[{"parts":[{"text":prompt}]}],
                    "tools":[{"google_search":{}}],
                }
                try:
                    r=await client.post(url, params={"key":self.api_key}, json=payload)
                    if r.status_code>=400:
                        errors.append(f"{model}: HTTP {r.status_code} {r.text[:250]}"); continue
                    data=r.json()
                    out=[]
                    seen=set()
                    for cand in data.get("candidates") or []:
                        gm=cand.get("groundingMetadata") or cand.get("grounding_metadata") or {}
                        for chunk in gm.get("groundingChunks") or gm.get("grounding_chunks") or []:
                            web=chunk.get("web") or {}
                            u=str(web.get("uri") or "").strip()
                            if not u or u in seen or not u.startswith(("http://","https://")):
                                continue
                            seen.add(u)
                            out.append({
                                "title": str(web.get("title") or "").strip(),
                                "url": u,
                                "snippet": str(web.get("text") or "").strip(),
                            })
                            if len(out)>=max_results: break
                        if len(out)>=max_results: break
                    if out:
                        self.model=model
                        return out[:max_results]
                    # Fallback: extract explicit URLs from grounded model text if chunks are absent.
                    texts=[]
                    for cand in data.get("candidates") or []:
                        texts += [str(p.get("text","")) for p in cand.get("content",{}).get("parts",[])]
                    urls=[]
                    for u in re.findall(r'https?://[^\s\]\)\>"\']+', "\n".join(texts)):
                        u=u.rstrip(".,);")
                        if u not in seen: urls.append(u); seen.add(u)
                    if urls:
                        self.model=model
                        return [{"title":"","url":u,"snippet":""} for u in urls[:max_results]]
                    errors.append(f"{model}: no grounded web sources")
                except Exception as exc:
                    errors.append(f"{model}: {exc}")
        raise RuntimeError("Gemini Google Search failed: " + " | ".join(errors)[-1800:])
