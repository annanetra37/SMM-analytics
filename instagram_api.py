"""
Instagram Graph API client for fetching business account analytics.
"""

import os
import time
from datetime import datetime, timedelta
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://graph.facebook.com/v19.0"


class InstagramAPI:
    def __init__(self, access_token: str | None = None, account_id: str | None = None):
        self.access_token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.account_id = account_id or os.getenv("INSTAGRAM_ACCOUNT_ID")
        if not self.access_token or not self.account_id:
            raise ValueError(
                "INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID must be set. "
                "See .env.example for details."
            )

    def _get(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        params = params or {}
        params["access_token"] = self.access_token
        resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _paginate(self, endpoint: str, params: dict | None = None, max_pages: int = 10) -> list[dict]:
        results = []
        params = params or {}
        params["access_token"] = self.access_token
        url = f"{BASE_URL}/{endpoint}"

        for _ in range(max_pages):
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            results.extend(data.get("data", []))
            paging = data.get("paging", {})
            next_url = paging.get("next")
            if not next_url:
                break
            url = next_url
            params = {}  # next_url already contains all params

        return results

    # ── Account Info ──────────────────────────────────────────────────

    def get_account_info(self) -> dict[str, Any]:
        fields = (
            "id,username,name,biography,followers_count,follows_count,"
            "media_count,profile_picture_url,website"
        )
        return self._get(self.account_id, {"fields": fields})

    # ── Account-Level Insights ────────────────────────────────────────

    def get_account_insights(self, period: str = "day", days: int = 30) -> dict[str, list]:
        since = int((datetime.now() - timedelta(days=days)).timestamp())
        until = int(datetime.now().timestamp())

        day_metrics = [
            "impressions",
            "reach",
            "profile_views",
            "website_clicks",
            "email_contacts",
            "phone_call_clicks",
            "text_message_clicks",
            "get_directions_clicks",
            "follower_count",
        ]

        results = {}

        # Day-period metrics
        try:
            data = self._get(
                f"{self.account_id}/insights",
                {
                    "metric": ",".join(day_metrics),
                    "period": "day",
                    "since": since,
                    "until": until,
                },
            )
            for item in data.get("data", []):
                results[item["name"]] = item.get("values", [])
        except requests.HTTPError:
            pass

        # Lifetime metrics (follower demographics)
        lifetime_metrics = [
            "audience_city",
            "audience_country",
            "audience_gender_age",
            "audience_locale",
        ]
        # Note: These were deprecated in v18+ in favor of the /insights demographic endpoint.
        # We'll try both approaches.
        try:
            data = self._get(
                f"{self.account_id}/insights",
                {"metric": ",".join(lifetime_metrics), "period": "lifetime"},
            )
            for item in data.get("data", []):
                results[item["name"]] = item.get("values", [])
        except requests.HTTPError:
            pass

        # Try the newer demographic breakdown endpoint
        demo_metrics = ["reached_audience_demographics", "engaged_audience_demographics", "follower_demographics"]
        for metric in demo_metrics:
            for breakdown in ["age", "gender", "city", "country"]:
                try:
                    data = self._get(
                        f"{self.account_id}/insights",
                        {
                            "metric": metric,
                            "period": "lifetime",
                            "metric_type": "total_value",
                            "breakdown": breakdown,
                        },
                    )
                    for item in data.get("data", []):
                        key = f"{item['name']}_{breakdown}"
                        total = item.get("total_value", {})
                        results[key] = total.get("breakdowns", [{}])[0].get("results", []) if total else []
                except requests.HTTPError:
                    pass

        return results

    # ── Online Followers (best posting times) ─────────────────────────

    def get_online_followers(self) -> dict[str, list]:
        try:
            data = self._get(
                f"{self.account_id}/insights",
                {"metric": "online_followers", "period": "lifetime"},
            )
            for item in data.get("data", []):
                if item["name"] == "online_followers":
                    return {"online_followers": item.get("values", [])}
        except requests.HTTPError:
            pass
        return {}

    # ── Media (Posts, Reels, Carousels) ───────────────────────────────

    def get_all_media(self, limit: int = 100) -> list[dict]:
        fields = (
            "id,caption,media_type,media_url,thumbnail_url,permalink,"
            "timestamp,like_count,comments_count,children"
        )
        media = self._paginate(
            f"{self.account_id}/media",
            {"fields": fields, "limit": min(limit, 50)},
            max_pages=(limit // 50) + 1,
        )
        return media[:limit]

    def get_media_insights(self, media_id: str, media_type: str) -> dict[str, Any]:
        if media_type in ("IMAGE", "CAROUSEL_ALBUM"):
            metrics = "impressions,reach,saved,video_views,likes,comments,shares"
        elif media_type == "VIDEO":
            metrics = "impressions,reach,saved,video_views,likes,comments,shares,plays"
        elif media_type == "REEL":
            metrics = "impressions,reach,saved,likes,comments,shares,plays,total_interactions"
        else:
            metrics = "impressions,reach,saved,likes,comments,shares"

        # Try full metrics first, fall back to fewer if some aren't available
        try:
            data = self._get(f"{media_id}/insights", {"metric": metrics})
            return {item["name"]: item["values"][0]["value"] for item in data.get("data", [])}
        except requests.HTTPError:
            # Fallback with basic metrics
            try:
                basic = "impressions,reach,saved"
                data = self._get(f"{media_id}/insights", {"metric": basic})
                return {item["name"]: item["values"][0]["value"] for item in data.get("data", [])}
            except requests.HTTPError:
                return {}

    def get_media_with_insights(self, limit: int = 100) -> list[dict]:
        media_list = self.get_all_media(limit)
        for media in media_list:
            # Rate-limit friendly: small delay between insight calls
            insights = self.get_media_insights(media["id"], media.get("media_type", "IMAGE"))
            media["insights"] = insights
            time.sleep(0.2)
        return media_list

    # ── Stories ───────────────────────────────────────────────────────

    def get_stories(self) -> list[dict]:
        try:
            fields = "id,media_type,media_url,timestamp"
            data = self._get(f"{self.account_id}/stories", {"fields": fields})
            stories = data.get("data", [])
            for story in stories:
                try:
                    metrics = "impressions,reach,replies,exits,taps_forward,taps_back"
                    insights = self._get(f"{story['id']}/insights", {"metric": metrics})
                    story["insights"] = {
                        item["name"]: item["values"][0]["value"]
                        for item in insights.get("data", [])
                    }
                except requests.HTTPError:
                    story["insights"] = {}
            return stories
        except requests.HTTPError:
            return []

    # ── Hashtag Search (limited by API) ───────────────────────────────

    def search_hashtag(self, hashtag_name: str) -> dict | None:
        try:
            data = self._get(
                "ig_hashtag_search",
                {"user_id": self.account_id, "q": hashtag_name},
            )
            results = data.get("data", [])
            return results[0] if results else None
        except requests.HTTPError:
            return None

    def get_hashtag_top_media(self, hashtag_id: str) -> list[dict]:
        try:
            fields = "id,caption,media_type,like_count,comments_count,timestamp,permalink"
            data = self._get(
                f"{hashtag_id}/top_media",
                {"user_id": self.account_id, "fields": fields},
            )
            return data.get("data", [])
        except requests.HTTPError:
            return []
