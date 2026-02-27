"""MLB Stats API client with retries, exponential backoff, and disk caching."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://statsapi.mlb.com/api/v1"


@dataclass
class MLBApiClient:
    """Small cached client for MLB Stats API responses."""

    cache_dir: Path = Path("cache")
    timeout: int = 45
    max_retries: int = 5
    backoff_factor: float = 0.6

    def __post_init__(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        retry = Retry(
            total=self.max_retries,
            connect=self.max_retries,
            read=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def get_json(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        use_v11: bool = False,
        sleep_s: float = 0.0,
    ) -> Dict[str, Any]:
        """GET endpoint and return parsed JSON, reading/writing cache transparently."""
        prefix = "https://statsapi.mlb.com/api/v1.1" if use_v11 else BASE_URL
        query = f"?{urlencode(params, doseq=True)}" if params else ""
        url = f"{prefix}{endpoint}{query}"

        cache_path = self._cache_path(url)
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        if sleep_s > 0:
            time.sleep(sleep_s)

        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        cache_path.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    def get_teams(self, season: int) -> list[dict[str, Any]]:
        data = self.get_json("/teams", {"sportId": 1, "season": season})
        teams = [
            t
            for t in data.get("teams", [])
            if t.get("active", True)
            and t.get("league", {}).get("id") in {103, 104}
            and t.get("sport", {}).get("id") == 1
        ]
        return teams

    def get_schedule_game_pks(self, season: int) -> list[int]:
        """Return unique gamePks for regular + postseason games."""
        data = self.get_json(
            "/schedule",
            {
                "sportId": 1,
                "season": season,
                "gameTypes": "R,F,D,L,W,S",
                "hydrate": "team",
            },
        )
        game_pks: set[int] = set()
        for date_row in data.get("dates", []):
            for game in date_row.get("games", []):
                game_pk = game.get("gamePk")
                if isinstance(game_pk, int):
                    game_pks.add(game_pk)
        return sorted(game_pks)

    def get_live_feed(self, game_pk: int) -> dict[str, Any]:
        return self.get_json(f"/game/{game_pk}/feed/live", use_v11=True)
