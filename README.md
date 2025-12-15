# 📰 Perplexity News Tracker

Automated news tracking system that fetches latest news from multiple categories using Perplexity API and saves to GitHub daily.

## 🎯 Features

- **8 News Categories**: Technology, Business, Sports, Entertainment, Science, Health, World, India
- **Automated Updates**: Runs every 6 hours via GitHub Actions
- **Organized Storage**: News saved as markdown files in `news/YYYY-MM-DD/` folders
- **Free & Open Source**: No cost, runs entirely on GitHub infrastructure

## 🚀 Quick Setup

### 1. Get Perplexity API Key

1. Visit [Perplexity API Settings](https://www.perplexity.ai/settings/api)
2. Generate a new API key (free tier available)
3. Copy the key

### 2. Add API Key to GitHub Secrets

1. Go to your repository **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `PERPLEXITY_API_KEY`
4. Value: Paste your API key
5. Click **Add secret**

### 3. Enable GitHub Actions

1. Go to **Actions** tab in your repository
2. Click **"I understand my workflows, go ahead and enable them"**
3. (Optional) Click **Run workflow** to test immediately

## 📅 Automation Schedule

- **Automatic**: Every 6 hours (0:00, 6:00, 12:00, 18:00 UTC)
- **Manual**: Click "Run workflow" in Actions tab anytime

## 📂 File Structure

```
perplexity-news-tracker/
├── .github/
│   └── workflows/
│       └── fetch-news.yml          # GitHub Actions workflow
├── scripts/
│   └── fetch_news.py            # Python script to fetch news
├── news/
│   ├── 2025-12-15/
│   │   ├── technology.md
│   │   ├── business.md
│   │   ├── sports.md
│   │   └── ...
│   └── 2025-12-16/
└── README.md
```

## ⚙️ Customization

### Change Categories

Edit `scripts/fetch_news.py` and modify the `CATEGORIES` dictionary:

```python
CATEGORIES = {
    "ai": "Artificial Intelligence news",
    "crypto": "Cryptocurrency updates",
    # Add your categories...
}
```

### Change Update Frequency

Edit `.github/workflows/fetch-news.yml` cron schedule:

```yaml
schedule:
  - cron: '0 */6 * * *'  # Every 6 hours
  # - cron: '0 0 * * *'  # Daily at midnight
  # - cron: '0 */3 * * *'  # Every 3 hours
```

## 📊 API Usage

**Perplexity Free Tier**: ~5 requests/day

- 8 categories × 4 runs/day = 32 requests/day
- **Recommendation**: Use paid tier or reduce frequency to 1-2 runs/day for free tier

## 🐛 Troubleshooting

### Workflow not running?
- Check if GitHub Actions are enabled
- Verify `PERPLEXITY_API_KEY` is added correctly
- Check Actions tab for error logs

### Demo mode showing?
- API key is missing or invalid
- Add/update the secret in repository settings

## 📝 License

MIT License - Feel free to use and modify!

## 👨‍💻 Author

Created by [myidkd1-coder](https://github.com/myidkd1-coder)

---

**⭐ Star this repo** if you find it useful!
