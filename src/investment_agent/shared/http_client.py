"""Generic async HTTP client for talking to internal APIs.

Centralizes timeout/base-url/JSON handling so each plugin's adapter doesn't
configure its own `httpx.AsyncClient`. Contains no knowledge of what data any
particular internal API returns - that parsing lives in the plugin's adapter.
"""

import httpx


class InternalApiClient:
    """Thin wrapper around `httpx.AsyncClient` for internal service calls."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        # `client` is injectable so tests can pass a pre-configured/mocked instance.
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def get_json(self, path: str, params: dict | None = None) -> dict:
        """GET `path` and return the parsed JSON body, raising on non-2xx responses."""
        response = await self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    async def aclose(self) -> None:
        """Release the underlying connection pool. Call once at app shutdown."""
        await self._client.aclose()
