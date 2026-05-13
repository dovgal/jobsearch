from __future__ import annotations

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1.5, min=2, max=20),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError)),
)
def post_json(
    url: str,
    *,
    headers: dict[str, str],
    json: dict,
    timeout: float = 180.0,
) -> dict:
    with httpx.Client(timeout=timeout) as cli:
        r = cli.post(url, headers=headers, json=json)
        if r.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{r.status_code} {r.reason_phrase}: {r.text[:600]}",
                request=r.request,
                response=r,
            )
        return r.json()
