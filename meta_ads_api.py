"""
Meta Marketing API client for fetching ad/boost campaign analytics.

Requires:
- A Facebook Ad Account ID (format: act_XXXXXXXXX)
- An access token with 'ads_read' permission
- The Instagram Account ID linked to the ad account

Docs: https://developers.facebook.com/docs/marketing-api/reference/ad-account/insights/
"""

import os
from datetime import datetime, timedelta
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://graph.facebook.com/v19.0"


class MetaAdsAPI:
    def __init__(
        self,
        access_token: str | None = None,
        ad_account_id: str | None = None,
    ):
        self.access_token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.ad_account_id = ad_account_id or os.getenv("META_AD_ACCOUNT_ID")
        if not self.access_token or not self.ad_account_id:
            raise ValueError(
                "Access token and META_AD_ACCOUNT_ID are required. "
                "The Ad Account ID should be in the format 'act_XXXXXXXXX'."
            )
        # Ensure the ad account ID has the act_ prefix
        if not self.ad_account_id.startswith("act_"):
            self.ad_account_id = f"act_{self.ad_account_id}"

    def _get(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        params = params or {}
        params["access_token"] = self.access_token
        resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _paginate(self, endpoint: str, params: dict | None = None, max_pages: int = 10) -> list[dict]:
        results: list[dict] = []
        params = params or {}
        params["access_token"] = self.access_token
        url = f"{BASE_URL}/{endpoint}"

        for _ in range(max_pages):
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            results.extend(data.get("data", []))
            next_url = data.get("paging", {}).get("next")
            if not next_url:
                break
            url = next_url
            params = {}
        return results

    # ── Account-Level Ad Insights ────────────────────────────────────

    def get_account_ad_insights(self, days: int = 30) -> list[dict]:
        """Get aggregated ad performance for the account over a time range."""
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        until = datetime.now().strftime("%Y-%m-%d")
        fields = (
            "spend,impressions,reach,clicks,cpc,cpm,ctr,cpp,"
            "frequency,actions,cost_per_action_type,"
            "objective,buying_type"
        )
        try:
            data = self._get(
                f"{self.ad_account_id}/insights",
                {
                    "fields": fields,
                    "time_range": f'{{"since":"{since}","until":"{until}"}}',
                    "filtering": '[{"field":"publisher_platform","operator":"IN","value":["instagram"]}]',
                    "level": "account",
                },
            )
            return data.get("data", [])
        except requests.HTTPError:
            return []

    # ── Campaign-Level Insights ──────────────────────────────────────

    def get_campaigns(self, days: int = 30) -> list[dict]:
        """List all campaigns with basic info."""
        fields = "id,name,objective,status,daily_budget,lifetime_budget,start_time,stop_time,buying_type"
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        until = datetime.now().strftime("%Y-%m-%d")
        try:
            return self._paginate(
                f"{self.ad_account_id}/campaigns",
                {
                    "fields": fields,
                    "time_range": f'{{"since":"{since}","until":"{until}"}}',
                    "filtering": '[{"field":"effective_status","operator":"IN","value":["ACTIVE","PAUSED","COMPLETED","CAMPAIGN_PAUSED"]}]',
                    "limit": 100,
                },
            )
        except requests.HTTPError:
            return []

    def get_campaign_insights(self, days: int = 30) -> list[dict]:
        """Get performance metrics broken down by campaign."""
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        until = datetime.now().strftime("%Y-%m-%d")
        fields = (
            "campaign_id,campaign_name,objective,spend,impressions,reach,"
            "clicks,cpc,cpm,ctr,frequency,actions,cost_per_action_type"
        )
        try:
            return self._paginate(
                f"{self.ad_account_id}/insights",
                {
                    "fields": fields,
                    "time_range": f'{{"since":"{since}","until":"{until}"}}',
                    "filtering": '[{"field":"publisher_platform","operator":"IN","value":["instagram"]}]',
                    "level": "campaign",
                    "limit": 100,
                },
            )
        except requests.HTTPError:
            return []

    # ── Ad Set-Level Insights ────────────────────────────────────────

    def get_adset_insights(self, days: int = 30) -> list[dict]:
        """Get performance broken down by ad set (targeting groups)."""
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        until = datetime.now().strftime("%Y-%m-%d")
        fields = (
            "adset_id,adset_name,campaign_name,spend,impressions,reach,"
            "clicks,cpc,cpm,ctr,frequency,actions,cost_per_action_type"
        )
        try:
            return self._paginate(
                f"{self.ad_account_id}/insights",
                {
                    "fields": fields,
                    "time_range": f'{{"since":"{since}","until":"{until}"}}',
                    "filtering": '[{"field":"publisher_platform","operator":"IN","value":["instagram"]}]',
                    "level": "adset",
                    "limit": 100,
                },
            )
        except requests.HTTPError:
            return []

    # ── Ad-Level Insights (Individual Boosted Posts) ─────────────────

    def get_ad_insights(self, days: int = 30) -> list[dict]:
        """Get performance for individual ads/boosted posts."""
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        until = datetime.now().strftime("%Y-%m-%d")
        fields = (
            "ad_id,ad_name,adset_name,campaign_name,objective,"
            "spend,impressions,reach,clicks,cpc,cpm,ctr,frequency,"
            "actions,cost_per_action_type"
        )
        try:
            return self._paginate(
                f"{self.ad_account_id}/insights",
                {
                    "fields": fields,
                    "time_range": f'{{"since":"{since}","until":"{until}"}}',
                    "filtering": '[{"field":"publisher_platform","operator":"IN","value":["instagram"]}]',
                    "level": "ad",
                    "limit": 200,
                },
            )
        except requests.HTTPError:
            return []

    # ── Placement Breakdown ──────────────────────────────────────────

    def get_placement_insights(self, days: int = 30) -> list[dict]:
        """Get performance broken down by Instagram placement (feed, stories, reels, explore)."""
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        until = datetime.now().strftime("%Y-%m-%d")
        fields = (
            "spend,impressions,reach,clicks,cpc,cpm,ctr,frequency,"
            "actions,cost_per_action_type"
        )
        try:
            return self._paginate(
                f"{self.ad_account_id}/insights",
                {
                    "fields": fields,
                    "time_range": f'{{"since":"{since}","until":"{until}"}}',
                    "filtering": '[{"field":"publisher_platform","operator":"IN","value":["instagram"]}]',
                    "breakdowns": "publisher_platform,platform_position",
                    "level": "account",
                    "limit": 50,
                },
            )
        except requests.HTTPError:
            return []

    # ── Daily Trend ──────────────────────────────────────────────────

    def get_daily_ad_insights(self, days: int = 30) -> list[dict]:
        """Get daily ad performance for trend analysis."""
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        until = datetime.now().strftime("%Y-%m-%d")
        fields = "spend,impressions,reach,clicks,cpc,cpm,ctr,actions"
        try:
            return self._paginate(
                f"{self.ad_account_id}/insights",
                {
                    "fields": fields,
                    "time_range": f'{{"since":"{since}","until":"{until}"}}',
                    "time_increment": 1,
                    "filtering": '[{"field":"publisher_platform","operator":"IN","value":["instagram"]}]',
                    "level": "account",
                    "limit": 90,
                },
            )
        except requests.HTTPError:
            return []

    # ── Objective Breakdown ──────────────────────────────────────────

    def get_objective_insights(self, days: int = 30) -> list[dict]:
        """Get performance broken down by campaign objective."""
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        until = datetime.now().strftime("%Y-%m-%d")
        fields = (
            "objective,spend,impressions,reach,clicks,cpc,cpm,ctr,"
            "frequency,actions,cost_per_action_type"
        )
        try:
            return self._paginate(
                f"{self.ad_account_id}/insights",
                {
                    "fields": fields,
                    "time_range": f'{{"since":"{since}","until":"{until}"}}',
                    "filtering": '[{"field":"publisher_platform","operator":"IN","value":["instagram"]}]',
                    "level": "campaign",
                    "limit": 100,
                },
            )
        except requests.HTTPError:
            return []
