from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests


class PolygonAPIError(RuntimeError):
    """Raised when Polygon responds with a non-success status."""


class PolygonRateLimitError(PolygonAPIError):
    """Raised when Polygon responds with HTTP 429 after retries."""


@dataclass(frozen=True)
class AggregateRequest:
    symbol: str
    multiplier: int
    timespan: str
    start: datetime
    end: datetime
    adjusted: bool

    def cache_key(self) -> Tuple[str, int, str, int, int, bool]:
        return (
            self.symbol,
            self.multiplier,
            self.timespan,
            int(self.start.timestamp() * 1000),
            int(self.end.timestamp() * 1000),
            self.adjusted,
        )


class PolygonAggregatorClient:
    """
    Thin HTTP client around Polygon's aggregate bars endpoint.

    The client reuses an underlying ``requests.Session`` for connection pooling,
    enforces a concurrency cap (default ``max_concurrent_requests`` = 5), and
    applies exponential backoff with jitter on HTTP 429/5xx responses. A small
    in-memory cache avoids duplicate requests within a downloader run.
    """

    BASE_URL = "https://api.polygon.io"

    def __init__(
        self,
        api_key: str,
        *,
        session: Optional[requests.Session] = None,
        max_retries: int = 5,
        backoff_factor: float = 1.5,
        max_concurrent_requests: int = 5,
    ) -> None:
        self._api_key = api_key
        self._session = session or requests.Session()
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._semaphore = threading.BoundedSemaphore(max_concurrent_requests)
        self._cache: Dict[Tuple[str, int, str, int, int, bool], List[dict]] = {}
        self._request_count = 0

    def get_aggregate_bars(
        self,
        symbol: str,
        multiplier: int,
        timespan: str,
        start: datetime,
        end: datetime,
        *,
        adjusted: bool = True,
        limit: int = 50_000,
    ) -> List[dict]:
        """
        Fetch aggregate bars for ``symbol`` within ``[start, end]``.

        Results are cached during the client's lifetime keyed by the request
        parameters to prevent redundant Polygon calls if the downloader retries.
        """

        request = AggregateRequest(symbol, multiplier, timespan, start, end, adjusted)
        cache_key = request.cache_key()
        if cache_key in self._cache:
            return self._cache[cache_key]

        results: List[dict] = []
        next_url: Optional[str] = self._build_url(request, limit)

        while next_url:
            payload = self._request_with_retries("GET", next_url)
            page_results = payload.get("results") or []
            results.extend(page_results)
            next_url = payload.get("next_url")
            if next_url:
                next_url = self._append_api_key(next_url)

        self._cache[cache_key] = results
        return results

    # ------------------------------------------------------------------ utils
    def _build_url(self, request: AggregateRequest, limit: int) -> str:
        start = request.start.astimezone(timezone.utc)
        end = request.end.astimezone(timezone.utc)
        start_token = start.date().isoformat()
        end_token = end.date().isoformat()
        return (
            f"{self.BASE_URL}/v2/aggs/ticker/{request.symbol}/range/"
            f"{request.multiplier}/{request.timespan}/"
            f"{start_token}/{end_token}"
            f"?adjusted={'true' if request.adjusted else 'false'}&limit={limit}&sort=asc"
            f"&apiKey={self._api_key}"
        )

    def _append_api_key(self, url: str) -> str:
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}apiKey={self._api_key}"

    def _request_with_retries(self, method: str, url: str) -> dict:
        attempt = 0
        last_exception: Optional[Exception] = None

        while attempt <= self._max_retries:
            with self._semaphore:
                try:
                    response = self._session.request(method, url, timeout=30)
                    self._request_count += 1
                except requests.RequestException as exc:
                    last_exception = exc
                    response = None

            if response is not None and response.status_code == 200:
                return response.json()

            attempt += 1

            status = response.status_code if response is not None else None
            if status == 429 and attempt > self._max_retries:
                raise PolygonRateLimitError("Polygon rate limit exceeded after retries")

            if response is not None and status not in (429, 500, 502, 503, 504):
                raise PolygonAPIError(
                    f"Polygon request failed with status {status}: {response.text}"
                )

            sleep_seconds = self._backoff_factor ** attempt
            sleep_seconds *= random.uniform(0.8, 1.2)
            time.sleep(min(sleep_seconds, 30))

        if last_exception:
            raise PolygonAPIError(f"Polygon request failed: {last_exception}") from last_exception
        raise PolygonAPIError("Polygon request failed without a response")

    @property
    def request_count(self) -> int:
        return self._request_count
