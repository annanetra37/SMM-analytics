# Instagram Business Analytics Dashboard

A comprehensive analytics dashboard for Instagram Business accounts, built with Python, Streamlit, and the Instagram Graph API. Designed for data-driven marketing strategy planning.

## KPIs & Metrics Covered

### Account Overview
- Followers, following, total posts, follow ratio
- Average engagement rate across all content

### Growth & Reach Trends
- Daily follower count with net growth and growth rate
- Daily reach and impressions with averages
- Impression frequency (impressions/reach)
- Profile views, website clicks, email/phone/directions clicks

### Content Performance
- Total likes, comments, saves, shares, reach, impressions
- Weekly engagement breakdown (stacked bar)
- Engagement rate distribution
- Performance by content type (IMAGE, VIDEO, REEL, CAROUSEL_ALBUM)
- Radar chart comparing content types
- Top 10 posts by engagement rate, reach, saves, and shares
- Full post-level data table

### Audience Demographics
- Gender distribution (pie chart)
- Age group distribution (bar chart)
- Top 20 cities and Top 15 countries

### Optimal Posting Times
- Engagement by day of week
- Engagement by hour of day
- Day x Hour heatmap
- Followers online by hour (from API)

### Hashtag Analysis
- Most used hashtags
- Best performing hashtags by engagement rate
- Hashtag count vs performance scatter plot

### Stories Performance
- Impressions, reach, replies, exits
- Story completion rate

### Marketing KPI Summary
- Awareness KPIs: reach, impressions, virality rate
- Engagement KPIs: ER, likes, comments, saves, save rate
- Growth KPIs: follower growth, growth rate, posting frequency
- Actionable insights table (best content type, best day/hour)

## Prerequisites

1. An **Instagram Business** or **Creator** account
2. A **Facebook Page** connected to the Instagram account
3. A **Meta Developer App** with Instagram Graph API access
4. A **long-lived access token**

## Setup

### 1. Get API Credentials

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a new app (type: Business)
3. Add the **Instagram Graph API** product
4. In the API Explorer, generate a User Token with these permissions:
   - `instagram_basic`
   - `instagram_manage_insights`
   - `pages_show_list`
   - `pages_read_engagement`
5. Exchange the short-lived token for a **long-lived token** (valid ~60 days):
   ```
   GET https://graph.facebook.com/v19.0/oauth/access_token?
     grant_type=fb_exchange_token&
     client_id={app-id}&
     client_secret={app-secret}&
     fb_exchange_token={short-lived-token}
   ```
6. Find your Instagram Business Account ID:
   ```
   GET https://graph.facebook.com/v19.0/me/accounts?access_token={token}
   ```
   Then for each page:
   ```
   GET https://graph.facebook.com/v19.0/{page-id}?fields=instagram_business_account&access_token={token}
   ```

### 2. Install & Run

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

Enter your Access Token and Account ID in the sidebar, or set them in a `.env` file:

```bash
cp .env.example .env
# Edit .env with your credentials
```

## Project Structure

```
SMM-analytics/
├── dashboard.py        # Streamlit dashboard (main entry point)
├── instagram_api.py    # Instagram Graph API client
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Notes

- **Stories data** is only available for stories posted within the last 24 hours
- **Demographic data** requires a minimum follower count (~100)
- **Rate limits**: The app includes small delays between API calls to avoid hitting Meta's rate limits
- **Token expiry**: Long-lived tokens last ~60 days. Set up token refresh for production use
- Data is cached for 15 minutes per session to minimize API calls
