"""
Instagram Business Analytics Dashboard
Comprehensive KPIs for data-driven marketing strategy.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from instagram_api import InstagramAPI
from meta_ads_api import MetaAdsAPI

st.set_page_config(
    page_title="Instagram Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    .metric-card h3 { margin: 0; font-size: 14px; opacity: 0.9; }
    .metric-card h1 { margin: 5px 0 0 0; font-size: 28px; }
    .stMetric > div { background-color: #f8f9fa; border-radius: 8px; padding: 10px; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.title("Instagram Analytics")
st.sidebar.markdown("---")

access_token = st.sidebar.text_input("Access Token", type="password", help="Your Instagram Graph API long-lived token")
account_id = st.sidebar.text_input("Account ID", help="Your Instagram Business Account ID")
ad_account_id = st.sidebar.text_input(
    "Ad Account ID (optional)",
    help="Your Meta Ad Account ID (format: act_XXXXXXXXX). Required for boost/ad analytics.",
)
days_range = st.sidebar.slider("Analysis Period (days)", 7, 90, 30)
media_limit = st.sidebar.slider("Posts to Analyze", 10, 200, 50)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Setup Guide:**\n"
    "1. Go to [Meta for Developers](https://developers.facebook.com/)\n"
    "2. Create an app and add Instagram Graph API\n"
    "3. Generate a long-lived access token\n"
    "4. Find your IG Business Account ID via the API Explorer"
)

if not access_token or not account_id:
    st.title("Instagram Business Analytics Dashboard")
    st.info("Enter your Instagram API credentials in the sidebar to get started.")
    st.markdown("""
    ### What you'll get:
    - **Account Overview** — followers, reach, impressions, profile activity
    - **Growth Tracking** — daily follower growth and reach trends
    - **Content Performance** — engagement rates, top posts, content type analysis
    - **Boost & Ad Strategy** — paid campaign comparison, ROI, placement analysis *(optional — requires Ad Account ID)*
    - **Audience Demographics** — age, gender, location breakdowns
    - **Optimal Posting Times** — when your followers are most active
    - **Engagement Analysis** — likes, comments, saves, shares breakdown
    - **Content Strategy Insights** — actionable recommendations
    """)
    st.stop()


# ── Load Data ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=900, show_spinner="Fetching Instagram data...")
def load_all_data(token: str, acc_id: str, days: int, limit: int):
    api = InstagramAPI(access_token=token, account_id=acc_id)

    account = api.get_account_info()
    insights = api.get_account_insights(days=days)
    online = api.get_online_followers()
    media = api.get_media_with_insights(limit=limit)
    stories = api.get_stories()

    return account, insights, online, media, stories


@st.cache_data(ttl=900, show_spinner="Fetching ad campaign data...")
def load_ads_data(token: str, ad_acc_id: str, days: int):
    ads_api = MetaAdsAPI(access_token=token, ad_account_id=ad_acc_id)

    account_ads = ads_api.get_account_ad_insights(days=days)
    campaigns = ads_api.get_campaigns(days=days)
    campaign_insights = ads_api.get_campaign_insights(days=days)
    ad_insights = ads_api.get_ad_insights(days=days)
    placement_insights = ads_api.get_placement_insights(days=days)
    daily_ads = ads_api.get_daily_ad_insights(days=days)

    return account_ads, campaigns, campaign_insights, ad_insights, placement_insights, daily_ads


try:
    account, insights, online_followers, media_list, stories = load_all_data(
        access_token, account_id, days_range, media_limit
    )
except Exception as e:
    st.error(f"Failed to fetch data: {e}")
    st.stop()

# Load ads data if Ad Account ID is provided
ads_data_loaded = False
if ad_account_id:
    try:
        (
            account_ads, campaigns, campaign_insights,
            ad_insights, placement_insights, daily_ads,
        ) = load_ads_data(access_token, ad_account_id, days_range)
        ads_data_loaded = True
    except Exception as e:
        st.sidebar.warning(f"Ad data unavailable: {e}")


# ── Helper Functions ──────────────────────────────────────────────────────────

def safe_metric(data: dict, key: str, default=0):
    values = data.get(key, [])
    if not values:
        return default
    if isinstance(values[0], dict):
        return values[-1].get("value", default)
    return values[-1] if values else default


def timeseries_from_insight(data: dict, key: str) -> pd.DataFrame:
    values = data.get(key, [])
    if not values or not isinstance(values[0], dict):
        return pd.DataFrame(columns=["date", "value"])
    rows = [{"date": v.get("end_time", "")[:10], "value": v.get("value", 0)} for v in values]
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def build_media_df(media: list[dict]) -> pd.DataFrame:
    rows = []
    for m in media:
        ins = m.get("insights", {})
        caption = m.get("caption", "") or ""
        rows.append({
            "id": m["id"],
            "type": m.get("media_type", "UNKNOWN"),
            "timestamp": m.get("timestamp", ""),
            "permalink": m.get("permalink", ""),
            "caption": caption[:80],
            "likes": m.get("like_count", 0) or ins.get("likes", 0),
            "comments": m.get("comments_count", 0) or ins.get("comments", 0),
            "impressions": ins.get("impressions", 0),
            "reach": ins.get("reach", 0),
            "saved": ins.get("saved", 0),
            "shares": ins.get("shares", 0),
            "plays": ins.get("plays", ins.get("video_views", 0)),
            "hashtags": len([w for w in caption.split() if w.startswith("#")]),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["engagement"] = df["likes"] + df["comments"] + df["saved"] + df["shares"]
        df["engagement_rate"] = (df["engagement"] / df["reach"].replace(0, 1) * 100).round(2)
        df["day_of_week"] = df["timestamp"].dt.day_name()
        df["hour"] = df["timestamp"].dt.hour
    return df


# ── Build DataFrames ──────────────────────────────────────────────────────────

media_df = build_media_df(media_list)

# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

st.title(f"📊 @{account.get('username', 'N/A')} — Analytics Dashboard")
st.caption(f"Analysis period: last {days_range} days | {len(media_df)} posts analyzed")

# ── 1. Account Overview KPIs ──────────────────────────────────────────────────

st.header("Account Overview")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Followers", f"{account.get('followers_count', 0):,}")
col2.metric("Following", f"{account.get('follows_count', 0):,}")
col3.metric("Total Posts", f"{account.get('media_count', 0):,}")

# Engagement rate (avg across analyzed posts)
avg_er = media_df["engagement_rate"].mean() if not media_df.empty else 0
col4.metric("Avg Engagement Rate", f"{avg_er:.2f}%")

# Follow ratio
followers = account.get("followers_count", 1)
following = account.get("follows_count", 1) or 1
col5.metric("Follow Ratio", f"{followers / following:.1f}:1")

# ── 2. Growth & Reach Trends ─────────────────────────────────────────────────

st.header("Growth & Reach Trends")

tab_growth, tab_reach, tab_impressions, tab_activity = st.tabs(
    ["Follower Growth", "Reach", "Impressions", "Profile Activity"]
)

with tab_growth:
    df_followers = timeseries_from_insight(insights, "follower_count")
    if not df_followers.empty:
        fig = px.area(df_followers, x="date", y="value", title="Daily Follower Count",
                      color_discrete_sequence=["#667eea"])
        fig.update_layout(xaxis_title="", yaxis_title="Followers")
        st.plotly_chart(fig, use_container_width=True)

        growth = df_followers["value"].iloc[-1] - df_followers["value"].iloc[0] if len(df_followers) > 1 else 0
        growth_pct = (growth / max(df_followers["value"].iloc[0], 1)) * 100
        c1, c2, c3 = st.columns(3)
        c1.metric("Net Growth", f"{growth:+,}")
        c2.metric("Growth Rate", f"{growth_pct:+.2f}%")
        c3.metric("Avg Daily Growth", f"{growth / max(len(df_followers), 1):+.1f}")
    else:
        st.info("Follower growth data not available for this period.")

with tab_reach:
    df_reach = timeseries_from_insight(insights, "reach")
    if not df_reach.empty:
        fig = px.bar(df_reach, x="date", y="value", title="Daily Reach",
                     color_discrete_sequence=["#764ba2"])
        fig.update_layout(xaxis_title="", yaxis_title="Accounts Reached")
        st.plotly_chart(fig, use_container_width=True)
        c1, c2 = st.columns(2)
        c1.metric("Total Reach", f"{df_reach['value'].sum():,}")
        c2.metric("Avg Daily Reach", f"{df_reach['value'].mean():,.0f}")
    else:
        st.info("Reach data not available.")

with tab_impressions:
    df_imp = timeseries_from_insight(insights, "impressions")
    if not df_imp.empty:
        fig = px.bar(df_imp, x="date", y="value", title="Daily Impressions",
                     color_discrete_sequence=["#f093fb"])
        fig.update_layout(xaxis_title="", yaxis_title="Impressions")
        st.plotly_chart(fig, use_container_width=True)

        total_imp = df_imp["value"].sum()
        total_reach = timeseries_from_insight(insights, "reach")["value"].sum()
        freq = total_imp / max(total_reach, 1)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Impressions", f"{total_imp:,}")
        c2.metric("Avg Daily Impressions", f"{df_imp['value'].mean():,.0f}")
        c3.metric("Frequency (Imp/Reach)", f"{freq:.2f}x")
    else:
        st.info("Impressions data not available.")

with tab_activity:
    activity_metrics = {
        "profile_views": "Profile Views",
        "website_clicks": "Website Clicks",
        "email_contacts": "Email Clicks",
        "phone_call_clicks": "Phone Clicks",
        "get_directions_clicks": "Directions Clicks",
        "text_message_clicks": "Text Clicks",
    }
    cols = st.columns(3)
    for i, (key, label) in enumerate(activity_metrics.items()):
        df_a = timeseries_from_insight(insights, key)
        total = df_a["value"].sum() if not df_a.empty else 0
        cols[i % 3].metric(label, f"{total:,}")

    df_pv = timeseries_from_insight(insights, "profile_views")
    if not df_pv.empty:
        fig = px.line(df_pv, x="date", y="value", title="Daily Profile Views",
                      color_discrete_sequence=["#4facfe"])
        st.plotly_chart(fig, use_container_width=True)


# ── 3. Content Performance ───────────────────────────────────────────────────

st.header("Content Performance")

if not media_df.empty:
    tab_overview, tab_types, tab_top, tab_detail = st.tabs(
        ["Overview", "By Content Type", "Top Performers", "All Posts"]
    )

    with tab_overview:
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total Likes", f"{media_df['likes'].sum():,}")
        c2.metric("Total Comments", f"{media_df['comments'].sum():,}")
        c3.metric("Total Saves", f"{media_df['saved'].sum():,}")
        c4.metric("Total Shares", f"{media_df['shares'].sum():,}")
        c5.metric("Total Reach", f"{media_df['reach'].sum():,}")
        c6.metric("Total Impressions", f"{media_df['impressions'].sum():,}")

        st.markdown("---")

        # Engagement over time
        daily_eng = media_df.set_index("timestamp").resample("W")[
            ["likes", "comments", "saved", "shares"]
        ].sum().reset_index()

        if not daily_eng.empty:
            fig = px.bar(daily_eng, x="timestamp",
                         y=["likes", "comments", "saved", "shares"],
                         title="Weekly Engagement Breakdown",
                         barmode="stack",
                         color_discrete_sequence=["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4"])
            fig.update_layout(xaxis_title="", yaxis_title="Engagements", legend_title="")
            st.plotly_chart(fig, use_container_width=True)

        # Engagement rate distribution
        fig = px.histogram(media_df, x="engagement_rate", nbins=20,
                           title="Engagement Rate Distribution",
                           color_discrete_sequence=["#667eea"])
        fig.update_layout(xaxis_title="Engagement Rate (%)", yaxis_title="Number of Posts")
        st.plotly_chart(fig, use_container_width=True)

    with tab_types:
        type_stats = media_df.groupby("type").agg(
            count=("id", "count"),
            avg_likes=("likes", "mean"),
            avg_comments=("comments", "mean"),
            avg_saves=("saved", "mean"),
            avg_shares=("shares", "mean"),
            avg_reach=("reach", "mean"),
            avg_impressions=("impressions", "mean"),
            avg_engagement_rate=("engagement_rate", "mean"),
        ).round(1).reset_index()

        st.dataframe(type_stats, use_container_width=True, hide_index=True)

        if len(type_stats) > 1:
            col1, col2 = st.columns(2)

            with col1:
                fig = px.bar(type_stats, x="type", y="avg_engagement_rate",
                             title="Avg Engagement Rate by Type",
                             color="type",
                             color_discrete_sequence=px.colors.qualitative.Set2)
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.bar(type_stats, x="type", y="avg_reach",
                             title="Avg Reach by Type",
                             color="type",
                             color_discrete_sequence=px.colors.qualitative.Set2)
                st.plotly_chart(fig, use_container_width=True)

            # Radar chart comparing content types
            categories = ["avg_likes", "avg_comments", "avg_saves", "avg_shares", "avg_reach"]
            fig = go.Figure()
            for _, row in type_stats.iterrows():
                # Normalize values to 0-100 for radar comparison
                vals = [row[c] for c in categories]
                max_val = max(vals) if max(vals) > 0 else 1
                normalized = [v / max_val * 100 for v in vals]
                fig.add_trace(go.Scatterpolar(
                    r=normalized + [normalized[0]],
                    theta=["Likes", "Comments", "Saves", "Shares", "Reach", "Likes"],
                    name=row["type"],
                    fill="toself",
                ))
            fig.update_layout(title="Content Type Comparison (Normalized)", polar=dict(radialaxis=dict(visible=True)))
            st.plotly_chart(fig, use_container_width=True)

    with tab_top:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Top 10 by Engagement Rate")
            top_er = media_df.nlargest(10, "engagement_rate")[
                ["caption", "type", "engagement_rate", "likes", "reach", "permalink"]
            ]
            st.dataframe(top_er, use_container_width=True, hide_index=True)

        with col2:
            st.subheader("Top 10 by Reach")
            top_reach = media_df.nlargest(10, "reach")[
                ["caption", "type", "reach", "impressions", "engagement_rate", "permalink"]
            ]
            st.dataframe(top_reach, use_container_width=True, hide_index=True)

        st.subheader("Top 10 by Saves")
        top_saves = media_df.nlargest(10, "saved")[
            ["caption", "type", "saved", "likes", "engagement_rate", "permalink"]
        ]
        st.dataframe(top_saves, use_container_width=True, hide_index=True)

        st.subheader("Top 10 by Shares")
        top_shares = media_df.nlargest(10, "shares")[
            ["caption", "type", "shares", "likes", "reach", "permalink"]
        ]
        st.dataframe(top_shares, use_container_width=True, hide_index=True)

    with tab_detail:
        st.dataframe(
            media_df[["timestamp", "type", "caption", "likes", "comments", "saved",
                       "shares", "reach", "impressions", "engagement_rate", "permalink"]],
            use_container_width=True,
            hide_index=True,
        )


# ── 4. Boost & Ad Strategy Performance ───────────────────────────────────────

st.header("Boost & Ad Strategy Performance")

if not ads_data_loaded:
    st.info(
        "Enter your **Meta Ad Account ID** in the sidebar to unlock boost/ad analytics. "
        "Format: `act_XXXXXXXXX`. Your access token needs the `ads_read` permission."
    )
else:

    # ── Helper: extract a specific action value from the actions list ──
    def _get_action_value(actions: list[dict] | None, action_type: str) -> int:
        if not actions:
            return 0
        for a in actions:
            if a.get("action_type") == action_type:
                return int(a.get("value", 0))
        return 0

    def _get_cost_per_action(costs: list[dict] | None, action_type: str) -> float:
        if not costs:
            return 0.0
        for a in costs:
            if a.get("action_type") == action_type:
                return float(a.get("value", 0))
        return 0.0

    # ── 4a. Boost Overview KPIs ──────────────────────────────────────
    ad_tabs = st.tabs([
        "Overview", "Campaign Comparison", "Strategy by Objective",
        "Placement Analysis", "Top Boosted Ads", "Spend Trend",
    ])

    with ad_tabs[0]:
        if account_ads:
            ad_summary = account_ads[0]
            total_spend = float(ad_summary.get("spend", 0))
            total_imp = int(ad_summary.get("impressions", 0))
            total_reach = int(ad_summary.get("reach", 0))
            total_clicks = int(ad_summary.get("clicks", 0))
            avg_cpm = float(ad_summary.get("cpm", 0))
            avg_cpc = float(ad_summary.get("cpc", 0))
            avg_ctr = float(ad_summary.get("ctr", 0))
            avg_freq = float(ad_summary.get("frequency", 0))

            actions = ad_summary.get("actions", [])
            total_follows = _get_action_value(actions, "page_engagement") + _get_action_value(actions, "like")
            total_link_clicks = _get_action_value(actions, "link_click")
            total_post_engagement = _get_action_value(actions, "post_engagement")
            total_messages = _get_action_value(actions, "onsite_conversion.messaging_conversation_started_7d")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Ad Spend", f"${total_spend:,.2f}")
            c2.metric("Paid Reach", f"{total_reach:,}")
            c3.metric("Paid Impressions", f"{total_imp:,}")
            c4.metric("Total Clicks", f"{total_clicks:,}")

            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Avg CPM", f"${avg_cpm:.2f}")
            c6.metric("Avg CPC", f"${avg_cpc:.2f}")
            c7.metric("Avg CTR", f"{avg_ctr:.2f}%")
            c8.metric("Avg Frequency", f"{avg_freq:.1f}x")

            c9, c10, c11, c12 = st.columns(4)
            c9.metric("Post Engagements", f"{total_post_engagement:,}")
            c10.metric("Link Clicks", f"{total_link_clicks:,}")
            c11.metric("Messages Started", f"{total_messages:,}")
            cost_per_engage = total_spend / max(total_post_engagement, 1)
            c12.metric("Cost per Engagement", f"${cost_per_engage:.3f}")

            # Organic vs Paid comparison
            if not media_df.empty:
                st.markdown("---")
                st.markdown("### Organic vs Paid Comparison")
                org_reach = media_df["reach"].sum()
                org_impressions = media_df["impressions"].sum()
                org_engagement = media_df["engagement"].sum()

                comp_col1, comp_col2, comp_col3 = st.columns(3)
                with comp_col1:
                    fig = go.Figure(data=[go.Bar(
                        x=["Organic", "Paid"],
                        y=[org_reach, total_reach],
                        marker_color=["#667eea", "#f093fb"],
                    )])
                    fig.update_layout(title="Reach: Organic vs Paid", yaxis_title="Accounts Reached")
                    st.plotly_chart(fig, use_container_width=True)

                with comp_col2:
                    fig = go.Figure(data=[go.Bar(
                        x=["Organic", "Paid"],
                        y=[org_impressions, total_imp],
                        marker_color=["#667eea", "#f093fb"],
                    )])
                    fig.update_layout(title="Impressions: Organic vs Paid", yaxis_title="Impressions")
                    st.plotly_chart(fig, use_container_width=True)

                with comp_col3:
                    fig = go.Figure(data=[go.Bar(
                        x=["Organic", "Paid"],
                        y=[org_engagement, total_post_engagement],
                        marker_color=["#667eea", "#f093fb"],
                    )])
                    fig.update_layout(title="Engagements: Organic vs Paid", yaxis_title="Engagements")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No ad performance data found for this period.")

    # ── 4b. Campaign Comparison ──────────────────────────────────────
    with ad_tabs[1]:
        if campaign_insights:
            camp_rows = []
            for c in campaign_insights:
                actions = c.get("actions", [])
                costs = c.get("cost_per_action_type", [])
                camp_rows.append({
                    "Campaign": c.get("campaign_name", "Unknown"),
                    "Objective": c.get("objective", "N/A"),
                    "Spend": float(c.get("spend", 0)),
                    "Impressions": int(c.get("impressions", 0)),
                    "Reach": int(c.get("reach", 0)),
                    "Clicks": int(c.get("clicks", 0)),
                    "CTR (%)": round(float(c.get("ctr", 0)), 2),
                    "CPC ($)": round(float(c.get("cpc", 0)), 2),
                    "CPM ($)": round(float(c.get("cpm", 0)), 2),
                    "Frequency": round(float(c.get("frequency", 0)), 1),
                    "Engagements": _get_action_value(actions, "post_engagement"),
                    "Link Clicks": _get_action_value(actions, "link_click"),
                    "Messages": _get_action_value(actions, "onsite_conversion.messaging_conversation_started_7d"),
                })
            camp_df = pd.DataFrame(camp_rows)

            st.dataframe(camp_df, use_container_width=True, hide_index=True)

            if len(camp_df) > 1:
                col1, col2 = st.columns(2)
                with col1:
                    fig = px.bar(
                        camp_df.nlargest(10, "Reach"),
                        x="Campaign", y="Reach",
                        title="Top Campaigns by Reach",
                        color="Objective",
                        color_discrete_sequence=px.colors.qualitative.Set2,
                    )
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    fig = px.bar(
                        camp_df.nlargest(10, "Engagements"),
                        x="Campaign", y="Engagements",
                        title="Top Campaigns by Engagements",
                        color="Objective",
                        color_discrete_sequence=px.colors.qualitative.Set2,
                    )
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)

                # Spend vs Results scatter
                fig = px.scatter(
                    camp_df, x="Spend", y="Reach", size="Engagements",
                    color="Objective", hover_name="Campaign",
                    title="Campaign ROI: Spend vs Reach (bubble = engagements)",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No campaign data found.")

    # ── 4c. Strategy by Objective ────────────────────────────────────
    with ad_tabs[2]:
        if campaign_insights:
            obj_rows = []
            for c in campaign_insights:
                actions = c.get("actions", [])
                obj_rows.append({
                    "objective": c.get("objective", "UNKNOWN"),
                    "spend": float(c.get("spend", 0)),
                    "impressions": int(c.get("impressions", 0)),
                    "reach": int(c.get("reach", 0)),
                    "clicks": int(c.get("clicks", 0)),
                    "ctr": float(c.get("ctr", 0)),
                    "engagements": _get_action_value(actions, "post_engagement"),
                    "link_clicks": _get_action_value(actions, "link_click"),
                    "messages": _get_action_value(actions, "onsite_conversion.messaging_conversation_started_7d"),
                })
            obj_df = pd.DataFrame(obj_rows)

            obj_summary = obj_df.groupby("objective").agg(
                campaigns=("objective", "count"),
                total_spend=("spend", "sum"),
                total_reach=("reach", "sum"),
                total_impressions=("impressions", "sum"),
                total_clicks=("clicks", "sum"),
                avg_ctr=("ctr", "mean"),
                total_engagements=("engagements", "sum"),
                total_link_clicks=("link_clicks", "sum"),
                total_messages=("messages", "sum"),
            ).round(2).reset_index()

            # Cost efficiency per objective
            obj_summary["cost_per_reach"] = (obj_summary["total_spend"] / obj_summary["total_reach"].replace(0, 1)).round(4)
            obj_summary["cost_per_engagement"] = (obj_summary["total_spend"] / obj_summary["total_engagements"].replace(0, 1)).round(4)

            st.markdown("### Performance by Campaign Objective")
            st.dataframe(obj_summary, use_container_width=True, hide_index=True)

            if len(obj_summary) > 1:
                col1, col2 = st.columns(2)
                with col1:
                    fig = px.bar(
                        obj_summary, x="objective", y="total_reach",
                        title="Total Reach by Objective",
                        color="objective",
                        color_discrete_sequence=px.colors.qualitative.Pastel,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    fig = px.bar(
                        obj_summary, x="objective", y="cost_per_engagement",
                        title="Cost per Engagement by Objective",
                        color="objective",
                        color_discrete_sequence=px.colors.qualitative.Pastel,
                    )
                    fig.update_layout(yaxis_title="Cost per Engagement ($)")
                    st.plotly_chart(fig, use_container_width=True)

                # Radar chart comparing objectives
                radar_cats = ["total_reach", "total_impressions", "total_clicks", "total_engagements", "total_messages"]
                fig = go.Figure()
                for _, row in obj_summary.iterrows():
                    vals = [row[c] for c in radar_cats]
                    max_val = max(vals) if max(vals) > 0 else 1
                    normalized = [v / max_val * 100 for v in vals]
                    labels = ["Reach", "Impressions", "Clicks", "Engagements", "Messages"]
                    fig.add_trace(go.Scatterpolar(
                        r=normalized + [normalized[0]],
                        theta=labels + [labels[0]],
                        name=row["objective"],
                        fill="toself",
                    ))
                fig.update_layout(title="Objective Strategy Comparison (Normalized)")
                st.plotly_chart(fig, use_container_width=True)

                # Best strategy recommendation
                if not obj_summary.empty:
                    best_reach = obj_summary.loc[obj_summary["total_reach"].idxmax(), "objective"]
                    best_engage = obj_summary.loc[obj_summary["total_engagements"].idxmax(), "objective"]
                    cheapest = obj_summary.loc[obj_summary["cost_per_engagement"].idxmin(), "objective"]

                    st.markdown("### Top Boost Strategies")
                    st.markdown(f"""
| Strategy Goal | Best Objective | Why |
|--------------|---------------|-----|
| Maximum Reach | **{best_reach}** | Highest total reach across campaigns |
| Most Engagement | **{best_engage}** | Drives the most post interactions |
| Most Cost-Efficient | **{cheapest}** | Lowest cost per engagement |
""")
        else:
            st.info("No campaign objective data found.")

    # ── 4d. Placement Analysis ───────────────────────────────────────
    with ad_tabs[3]:
        if placement_insights:
            place_rows = []
            for p in placement_insights:
                actions = p.get("actions", [])
                place_rows.append({
                    "Placement": p.get("platform_position", "Unknown"),
                    "Spend": float(p.get("spend", 0)),
                    "Impressions": int(p.get("impressions", 0)),
                    "Reach": int(p.get("reach", 0)),
                    "Clicks": int(p.get("clicks", 0)),
                    "CTR (%)": round(float(p.get("ctr", 0)), 2),
                    "CPC ($)": round(float(p.get("cpc", 0)), 2),
                    "CPM ($)": round(float(p.get("cpm", 0)), 2),
                    "Engagements": _get_action_value(actions, "post_engagement"),
                })
            place_df = pd.DataFrame(place_rows)

            st.dataframe(place_df, use_container_width=True, hide_index=True)

            if len(place_df) > 1:
                col1, col2 = st.columns(2)
                with col1:
                    fig = px.pie(
                        place_df, names="Placement", values="Spend",
                        title="Ad Spend by Placement",
                        color_discrete_sequence=px.colors.qualitative.Set2,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    fig = px.pie(
                        place_df, names="Placement", values="Reach",
                        title="Reach by Placement",
                        color_discrete_sequence=px.colors.qualitative.Pastel,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Efficiency comparison
                place_df["Cost per 1K Reach"] = (place_df["Spend"] / place_df["Reach"].replace(0, 1) * 1000).round(2)
                fig = px.bar(
                    place_df, x="Placement", y="Cost per 1K Reach",
                    title="Cost per 1,000 Reach by Placement (lower = better)",
                    color="Placement",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig.update_layout(yaxis_title="$ per 1,000 Reach")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No placement breakdown data found.")

    # ── 4e. Top Boosted Ads ──────────────────────────────────────────
    with ad_tabs[4]:
        if ad_insights:
            ad_rows = []
            for a in ad_insights:
                actions = a.get("actions", [])
                ad_rows.append({
                    "Ad Name": a.get("ad_name", "Unknown"),
                    "Campaign": a.get("campaign_name", ""),
                    "Objective": a.get("objective", "N/A"),
                    "Spend": float(a.get("spend", 0)),
                    "Reach": int(a.get("reach", 0)),
                    "Impressions": int(a.get("impressions", 0)),
                    "Clicks": int(a.get("clicks", 0)),
                    "CTR (%)": round(float(a.get("ctr", 0)), 2),
                    "CPC ($)": round(float(a.get("cpc", 0)), 2),
                    "Engagements": _get_action_value(actions, "post_engagement"),
                    "Link Clicks": _get_action_value(actions, "link_click"),
                    "Messages": _get_action_value(actions, "onsite_conversion.messaging_conversation_started_7d"),
                })
            ads_df = pd.DataFrame(ad_rows)

            st.subheader("Top 10 Ads by Reach")
            st.dataframe(ads_df.nlargest(10, "Reach"), use_container_width=True, hide_index=True)

            st.subheader("Top 10 Ads by Engagements")
            st.dataframe(ads_df.nlargest(10, "Engagements"), use_container_width=True, hide_index=True)

            st.subheader("Top 10 Ads by Messages Started")
            st.dataframe(ads_df.nlargest(10, "Messages"), use_container_width=True, hide_index=True)

            # Most cost-efficient ads
            ads_df["Cost per Engagement"] = (ads_df["Spend"] / ads_df["Engagements"].replace(0, 1)).round(3)
            efficient = ads_df[ads_df["Engagements"] > 0].nsmallest(10, "Cost per Engagement")
            if not efficient.empty:
                st.subheader("Top 10 Most Cost-Efficient Ads")
                st.dataframe(efficient, use_container_width=True, hide_index=True)
        else:
            st.info("No individual ad data found.")

    # ── 4f. Spend Trend ──────────────────────────────────────────────
    with ad_tabs[5]:
        if daily_ads:
            trend_rows = []
            for d in daily_ads:
                actions = d.get("actions", [])
                trend_rows.append({
                    "date": d.get("date_start", ""),
                    "spend": float(d.get("spend", 0)),
                    "impressions": int(d.get("impressions", 0)),
                    "reach": int(d.get("reach", 0)),
                    "clicks": int(d.get("clicks", 0)),
                    "cpm": float(d.get("cpm", 0)),
                    "ctr": float(d.get("ctr", 0)),
                    "engagements": _get_action_value(actions, "post_engagement"),
                })
            trend_df = pd.DataFrame(trend_rows)
            trend_df["date"] = pd.to_datetime(trend_df["date"])

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(
                go.Bar(x=trend_df["date"], y=trend_df["spend"], name="Spend ($)", marker_color="#f093fb"),
                secondary_y=False,
            )
            fig.add_trace(
                go.Scatter(x=trend_df["date"], y=trend_df["reach"], name="Reach", marker_color="#667eea", mode="lines+markers"),
                secondary_y=True,
            )
            fig.update_layout(title="Daily Ad Spend vs Reach")
            fig.update_yaxes(title_text="Spend ($)", secondary_y=False)
            fig.update_yaxes(title_text="Reach", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)

            # Engagement trend
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(
                go.Bar(x=trend_df["date"], y=trend_df["engagements"], name="Engagements", marker_color="#4ecdc4"),
                secondary_y=False,
            )
            fig.add_trace(
                go.Scatter(x=trend_df["date"], y=trend_df["ctr"], name="CTR %", marker_color="#ff6b6b", mode="lines+markers"),
                secondary_y=True,
            )
            fig.update_layout(title="Daily Ad Engagements vs CTR")
            fig.update_yaxes(title_text="Engagements", secondary_y=False)
            fig.update_yaxes(title_text="CTR %", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)

            # Cumulative spend
            trend_df["cumulative_spend"] = trend_df["spend"].cumsum()
            trend_df["cumulative_reach"] = trend_df["reach"].cumsum()
            fig = px.area(trend_df, x="date", y="cumulative_spend",
                          title="Cumulative Ad Spend Over Time",
                          color_discrete_sequence=["#764ba2"])
            fig.update_layout(yaxis_title="Cumulative Spend ($)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No daily ad trend data found.")


# ── 5. Audience Demographics ──────────────────────────────────────────────────

st.header("Audience Demographics")

demo_tabs = st.tabs(["Gender & Age", "Locations"])

with demo_tabs[0]:
    # Try newer endpoint keys first, then legacy
    gender_age_data = (
        insights.get("follower_demographics_gender", [])
        or insights.get("audience_gender_age", [{}])[0].get("value", {}) if insights.get("audience_gender_age") else {}
    )

    if isinstance(gender_age_data, list) and gender_age_data:
        # New format: list of {dimension_values: [...], value: N}
        ga_rows = []
        for item in gender_age_data:
            dims = item.get("dimension_values", [])
            if len(dims) >= 2:
                ga_rows.append({"gender": dims[0], "age": dims[1], "count": item.get("value", 0)})
            elif len(dims) == 1:
                ga_rows.append({"gender": dims[0], "age": "all", "count": item.get("value", 0)})
        if ga_rows:
            ga_df = pd.DataFrame(ga_rows)
            col1, col2 = st.columns(2)
            with col1:
                gender_totals = ga_df.groupby("gender")["count"].sum().reset_index()
                fig = px.pie(gender_totals, names="gender", values="count",
                             title="Gender Distribution",
                             color_discrete_sequence=["#667eea", "#f093fb", "#4facfe"])
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                age_totals = ga_df.groupby("age")["count"].sum().reset_index()
                fig = px.bar(age_totals, x="age", y="count",
                             title="Age Distribution",
                             color_discrete_sequence=["#764ba2"])
                st.plotly_chart(fig, use_container_width=True)
    elif isinstance(gender_age_data, dict) and gender_age_data:
        # Legacy format: {"F.18-24": 123, "M.25-34": 456, ...}
        ga_rows = []
        for key, val in gender_age_data.items():
            parts = key.split(".")
            if len(parts) == 2:
                ga_rows.append({"gender": parts[0], "age": parts[1], "count": val})
        if ga_rows:
            ga_df = pd.DataFrame(ga_rows)
            col1, col2 = st.columns(2)
            with col1:
                gender_totals = ga_df.groupby("gender")["count"].sum().reset_index()
                gender_totals["gender"] = gender_totals["gender"].map({"F": "Female", "M": "Male", "U": "Unknown"})
                fig = px.pie(gender_totals, names="gender", values="count",
                             title="Gender Distribution",
                             color_discrete_sequence=["#667eea", "#f093fb", "#4facfe"])
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                age_totals = ga_df.groupby("age")["count"].sum().reset_index()
                fig = px.bar(age_totals, x="age", y="count",
                             title="Age Distribution",
                             color_discrete_sequence=["#764ba2"])
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Gender/age demographic data not available. Requires a Business or Creator account with sufficient followers.")

with demo_tabs[1]:
    # Cities
    city_data = (
        insights.get("follower_demographics_city", [])
        or insights.get("audience_city", [{}])[0].get("value", {}) if insights.get("audience_city") else {}
    )

    if isinstance(city_data, list) and city_data:
        city_rows = [{"city": item.get("dimension_values", ["Unknown"])[0], "count": item.get("value", 0)}
                     for item in city_data]
        city_df = pd.DataFrame(city_rows).nlargest(20, "count")
        fig = px.bar(city_df, x="count", y="city", orientation="h",
                     title="Top 20 Cities",
                     color_discrete_sequence=["#4facfe"])
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)
    elif isinstance(city_data, dict) and city_data:
        city_df = pd.DataFrame(list(city_data.items()), columns=["city", "count"]).nlargest(20, "count")
        fig = px.bar(city_df, x="count", y="city", orientation="h",
                     title="Top 20 Cities",
                     color_discrete_sequence=["#4facfe"])
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("City data not available.")

    # Countries
    country_data = (
        insights.get("follower_demographics_country", [])
        or insights.get("audience_country", [{}])[0].get("value", {}) if insights.get("audience_country") else {}
    )

    if isinstance(country_data, list) and country_data:
        country_rows = [{"country": item.get("dimension_values", ["Unknown"])[0], "count": item.get("value", 0)}
                        for item in country_data]
        country_df = pd.DataFrame(country_rows).nlargest(15, "count")
        fig = px.bar(country_df, x="count", y="country", orientation="h",
                     title="Top 15 Countries",
                     color_discrete_sequence=["#764ba2"])
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)
    elif isinstance(country_data, dict) and country_data:
        country_df = pd.DataFrame(list(country_data.items()), columns=["country", "count"]).nlargest(15, "count")
        fig = px.bar(country_df, x="count", y="country", orientation="h",
                     title="Top 15 Countries",
                     color_discrete_sequence=["#764ba2"])
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Country data not available.")


# ── 5. Optimal Posting Times ─────────────────────────────────────────────────

st.header("Optimal Posting Times")

if not media_df.empty:
    col1, col2 = st.columns(2)

    with col1:
        # Engagement by day of week
        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_stats = media_df.groupby("day_of_week").agg(
            avg_engagement=("engagement", "mean"),
            avg_er=("engagement_rate", "mean"),
            count=("id", "count"),
        ).reindex(dow_order).reset_index()

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=dow_stats["day_of_week"], y=dow_stats["avg_engagement"],
                             name="Avg Engagement", marker_color="#667eea"), secondary_y=False)
        fig.add_trace(go.Scatter(x=dow_stats["day_of_week"], y=dow_stats["avg_er"],
                                 name="Avg ER %", marker_color="#f093fb", mode="lines+markers"),
                      secondary_y=True)
        fig.update_layout(title="Performance by Day of Week")
        fig.update_yaxes(title_text="Avg Engagement", secondary_y=False)
        fig.update_yaxes(title_text="Engagement Rate %", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Engagement by hour
        hour_stats = media_df.groupby("hour").agg(
            avg_engagement=("engagement", "mean"),
            avg_er=("engagement_rate", "mean"),
            count=("id", "count"),
        ).reset_index()

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=hour_stats["hour"], y=hour_stats["avg_engagement"],
                             name="Avg Engagement", marker_color="#764ba2"), secondary_y=False)
        fig.add_trace(go.Scatter(x=hour_stats["hour"], y=hour_stats["avg_er"],
                                 name="Avg ER %", marker_color="#4facfe", mode="lines+markers"),
                      secondary_y=True)
        fig.update_layout(title="Performance by Hour of Day")
        fig.update_xaxes(dtick=1)
        fig.update_yaxes(title_text="Avg Engagement", secondary_y=False)
        fig.update_yaxes(title_text="Engagement Rate %", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

    # Heatmap: day x hour
    if len(media_df) >= 10:
        heatmap_data = media_df.groupby(["day_of_week", "hour"])["engagement_rate"].mean().reset_index()
        heatmap_pivot = heatmap_data.pivot(index="day_of_week", columns="hour", values="engagement_rate")
        heatmap_pivot = heatmap_pivot.reindex(dow_order)

        fig = px.imshow(heatmap_pivot, title="Engagement Rate Heatmap (Day x Hour)",
                        labels=dict(x="Hour", y="Day", color="ER %"),
                        color_continuous_scale="Viridis", aspect="auto")
        st.plotly_chart(fig, use_container_width=True)

    # Online followers data
    online_data = online_followers.get("online_followers", [])
    if online_data:
        for entry in online_data:
            val = entry.get("value", {})
            if isinstance(val, dict) and val:
                hours = sorted(val.items(), key=lambda x: int(x[0]))
                of_df = pd.DataFrame(hours, columns=["hour", "followers_online"])
                of_df["hour"] = of_df["hour"].astype(int)
                fig = px.bar(of_df, x="hour", y="followers_online",
                             title="Followers Online by Hour (from API)",
                             color_discrete_sequence=["#96ceb4"])
                fig.update_xaxes(dtick=1)
                st.plotly_chart(fig, use_container_width=True)
                break


# ── 6. Hashtag Analysis ──────────────────────────────────────────────────────

st.header("Hashtag Analysis")

if not media_df.empty:
    # Extract hashtags from captions
    all_hashtags = []
    for _, row in media_df.iterrows():
        caption = row.get("caption", "") or ""
        # The media_df caption is truncated to 80 chars; re-parse from raw media list
        tags = [w.lower().strip("#.,!?") for w in caption.split() if w.startswith("#")]
        for tag in tags:
            if tag:
                all_hashtags.append({"hashtag": f"#{tag}", "engagement": row["engagement"],
                                     "reach": row["reach"], "engagement_rate": row["engagement_rate"]})

    if all_hashtags:
        ht_df = pd.DataFrame(all_hashtags)
        ht_stats = ht_df.groupby("hashtag").agg(
            usage_count=("hashtag", "count"),
            avg_engagement=("engagement", "mean"),
            avg_reach=("reach", "mean"),
            avg_er=("engagement_rate", "mean"),
        ).round(2).reset_index()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Most Used Hashtags")
            top_used = ht_stats.nlargest(15, "usage_count")
            fig = px.bar(top_used, x="usage_count", y="hashtag", orientation="h",
                         color_discrete_sequence=["#667eea"])
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Best Performing Hashtags (by ER)")
            # Only show hashtags used at least twice
            frequent = ht_stats[ht_stats["usage_count"] >= 2].nlargest(15, "avg_er")
            if not frequent.empty:
                fig = px.bar(frequent, x="avg_er", y="hashtag", orientation="h",
                             color_discrete_sequence=["#f093fb"])
                fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Avg Engagement Rate %")
                st.plotly_chart(fig, use_container_width=True)

        # Hashtag count vs performance
        ht_count_perf = media_df.groupby("hashtags").agg(
            post_count=("id", "count"),
            avg_er=("engagement_rate", "mean"),
            avg_reach=("reach", "mean"),
        ).reset_index()

        fig = px.scatter(ht_count_perf, x="hashtags", y="avg_er", size="post_count",
                         title="Number of Hashtags vs Engagement Rate",
                         color_discrete_sequence=["#764ba2"],
                         labels={"hashtags": "# of Hashtags", "avg_er": "Avg ER %"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hashtags found in post captions.")


# ── 7. Stories Performance ───────────────────────────────────────────────────

st.header("Stories Performance")

if stories:
    story_rows = []
    for s in stories:
        ins = s.get("insights", {})
        story_rows.append({
            "timestamp": s.get("timestamp", ""),
            "type": s.get("media_type", ""),
            "impressions": ins.get("impressions", 0),
            "reach": ins.get("reach", 0),
            "replies": ins.get("replies", 0),
            "exits": ins.get("exits", 0),
            "taps_forward": ins.get("taps_forward", 0),
            "taps_back": ins.get("taps_back", 0),
        })
    story_df = pd.DataFrame(story_rows)

    if not story_df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Avg Impressions", f"{story_df['impressions'].mean():,.0f}")
        c2.metric("Avg Reach", f"{story_df['reach'].mean():,.0f}")
        c3.metric("Total Replies", f"{story_df['replies'].sum():,}")
        c4.metric("Avg Exit Rate", f"{(story_df['exits'].sum() / max(story_df['impressions'].sum(), 1) * 100):.1f}%")

        # Completion rate = 1 - (exits / impressions)
        story_df["completion_rate"] = (1 - story_df["exits"] / story_df["impressions"].replace(0, 1)) * 100
        st.metric("Avg Story Completion Rate", f"{story_df['completion_rate'].mean():.1f}%")
else:
    st.info("No active stories found. Stories data is only available for stories posted in the last 24 hours.")


# ── 8. Content Strategy KPI Summary ──────────────────────────────────────────

st.header("Marketing KPI Summary")

if not media_df.empty:
    st.markdown("### Key Metrics for Your Marketing Plan")

    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

    with kpi_col1:
        st.markdown("**Awareness KPIs**")
        total_reach_posts = media_df["reach"].sum()
        total_imp_posts = media_df["impressions"].sum()
        st.metric("Total Content Reach", f"{total_reach_posts:,}")
        st.metric("Total Impressions", f"{total_imp_posts:,}")
        st.metric("Avg Reach per Post", f"{media_df['reach'].mean():,.0f}")
        viral_rate = (media_df[media_df["shares"] > 0].shape[0] / len(media_df) * 100) if len(media_df) > 0 else 0
        st.metric("Virality Rate (posts w/ shares)", f"{viral_rate:.1f}%")

    with kpi_col2:
        st.markdown("**Engagement KPIs**")
        st.metric("Avg Engagement Rate", f"{media_df['engagement_rate'].mean():.2f}%")
        st.metric("Avg Likes/Post", f"{media_df['likes'].mean():,.0f}")
        st.metric("Avg Comments/Post", f"{media_df['comments'].mean():,.1f}")
        st.metric("Avg Saves/Post", f"{media_df['saved'].mean():,.1f}")
        save_rate = (media_df["saved"].sum() / max(media_df["reach"].sum(), 1)) * 100
        st.metric("Save Rate", f"{save_rate:.2f}%")

    with kpi_col3:
        st.markdown("**Growth KPIs**")
        st.metric("Followers", f"{account.get('followers_count', 0):,}")
        df_fc = timeseries_from_insight(insights, "follower_count")
        if not df_fc.empty and len(df_fc) > 1:
            net_g = df_fc["value"].iloc[-1] - df_fc["value"].iloc[0]
            st.metric("Net Follower Growth", f"{net_g:+,}")
            st.metric("Growth Rate", f"{(net_g / max(df_fc['value'].iloc[0], 1) * 100):+.2f}%")

        # Content velocity
        if not media_df.empty:
            date_range = (media_df["timestamp"].max() - media_df["timestamp"].min()).days or 1
            posts_per_week = len(media_df) / date_range * 7
            st.metric("Posting Frequency", f"{posts_per_week:.1f} posts/week")

    st.markdown("---")

    # Best performing content summary
    st.markdown("### Actionable Insights")

    best_type = media_df.groupby("type")["engagement_rate"].mean().idxmax() if len(media_df.groupby("type")) > 0 else "N/A"
    best_day = media_df.groupby("day_of_week")["engagement_rate"].mean().idxmax() if len(media_df) > 0 else "N/A"
    best_hour = media_df.groupby("hour")["engagement_rate"].mean().idxmax() if len(media_df) > 0 else "N/A"

    insights_text = f"""
    | Insight | Value |
    |---------|-------|
    | Best Content Type | **{best_type}** |
    | Best Day to Post | **{best_day}** |
    | Best Hour to Post | **{best_hour}:00** |
    | Avg Engagement Rate | **{media_df['engagement_rate'].mean():.2f}%** |
    | Highest ER Post | **{media_df['engagement_rate'].max():.2f}%** |
    | Posts Analyzed | **{len(media_df)}** |
    """
    st.markdown(insights_text)

st.markdown("---")
st.caption("Data sourced from Instagram Graph API. Dashboard refreshes every 15 minutes when reloaded.")
