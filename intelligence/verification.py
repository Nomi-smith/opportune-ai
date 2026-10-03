from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

async def verify_opportunity(opportunity):
    url = opportunity.application_url or opportunity.source_url

    if not url:
        opportunity.verification_status = "NOT_FOUND"
        return opportunity

    host = urlparse(url).netloc.lower()
    if not host:
        opportunity.verification_status = "UNVERIFIED"
        return opportunity

    try:
        async with httpx.AsyncClient(
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "OpportuneAI/0.2 public research"},
        ) as client:
            response = await client.get(url)

        if response.status_code < 400:
            opportunity.verification_status = "PARTIALLY_VERIFIED"
            opportunity.last_verified = datetime.now(timezone.utc).isoformat()
            opportunity.metadata["verified_http_status"] = response.status_code
            opportunity.metadata["verified_host"] = urlparse(str(response.url)).netloc
        else:
            opportunity.verification_status = "UNVERIFIED"
    except Exception:
        opportunity.verification_status = "UNVERIFIED"

    return opportunity
