#!/usr/bin/env python3
"""
Perplexity News Tracker with Full Article Scraping
- Fetches top 5 news items per category from Perplexity API
- Scrapes full article content from source URLs
- Saves each article as separate markdown file
- Creates category index with all articles

DISCLAIMER: Content is scraped from public sources with attribution.
Users assume all risk. Verify licensing before redistribution.
"""

import os
import re
import json
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from newspaper import Article

CATEGORIES = {
    "technology": "Latest technology news and innovations",
    "business": "Business and economy news updates",
    "sports": "Sports news and highlights",
    "entertainment": "Entertainment and celebrity news",
    "science": "Science discoveries and research",
    "health": "Health and medical news",
    "world": "World news and international events",
    "india": "Latest news from India",
}

API_URL = "https://api.perplexity.ai/chat/completions"

def now_utc_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def today_yyyy_mm_dd():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def slugify(text: str, max_len: int = 80) -> str:
    text = text.strip().lower()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if not text:
        return "untitled"
    return text[:max_len].strip("-")

def short_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]

def load_state(state_path: Path) -> dict:
    if state_path.exists():
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            return {"seen": []}
    return {"seen": []}

def save_state(state_path: Path, state: dict):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def perplexity_request(api_key: str, category: str, description: str):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "url": {"type": "string"},
                        "publisher": {"type": "string"},
                        "published_date": {"type": "string"},
                    },
                    "required": ["title", "summary", "url"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    }

    payload = {
        "model": "sonar",
        "search_mode": "web",
        "temperature": 0.2,
        "max_tokens": 900,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return ONLY valid JSON matching the schema. "
                    "No bracket citations. Use real URLs. "
                    "Summaries: 2-4 lines, original wording."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Category: {category}\n"
                    f"Find top 5 latest {description}.\n"
                    f"Return 5 items with title, summary, url, publisher, published_date."
                ),
            },
        ],
        "response_format": {"type": "json_schema", "json_schema": {"schema": schema}},
    }

    r = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    return r

def scrape_full_article(url: str) -> dict:
    """
    Scrape full article from URL using newspaper3k.
    Returns: {title, text, authors, publish_date, top_image}
    """
    try:
        print(f"    Scraping: {url[:60]}...")
        article = Article(url)
        article.download()
        article.parse()
        
        return {
            "title": article.title or "",
            "text": article.text or "",
            "authors": article.authors or [],
            "publish_date": str(article.publish_date) if article.publish_date else "",
            "top_image": article.top_image or "",
        }
    except Exception as e:
        print(f"    ⚠️  Scrape failed: {e}")
        return {"title": "", "text": "", "authors": [], "publish_date": "", "top_image": ""}

def write_post_file(base_dir: Path, category: str, item: dict, scraped: dict):
    title = item.get("title", "").strip() or scraped.get("title", "Untitled")
    url = item.get("url", "").strip()
    summary = item.get("summary", "").strip()
    publisher = item.get("publisher", "").strip()
    published_date = item.get("published_date", "").strip() or scraped.get("publish_date", "")
    
    full_text = scraped.get("text", "").strip()
    authors = scraped.get("authors", [])
    top_image = scraped.get("top_image", "")

    slug = slugify(title)
    uniq = short_hash(url or title or now_utc_iso())
    filename = f"{slug}-{uniq}.md"

    out_dir = base_dir / category
    out_dir.mkdir(parents=True, exist_ok=True)

    md = []
    md.append(f"# {title}")
    md.append("")
    
    # Metadata
    md.append(f"**Category:** {category.title()}")
    md.append(f"**Source:** [{url}]({url})")
    if publisher:
        md.append(f"**Publisher:** {publisher}")
    if authors:
        md.append(f"**Authors:** {', '.join(authors)}")
    if published_date:
        md.append(f"**Published:** {published_date}")
    md.append(f"**Scraped (UTC):** {now_utc_iso()}")
    md.append("")
    
    # Top image
    if top_image:
        md.append(f"![Article Image]({top_image})")
        md.append("")
    
    # Summary from Perplexity
    if summary:
        md.append("## Summary")
        md.append(summary)
        md.append("")
    
    # Full article text
    if full_text:
        md.append("## Full Article")
        md.append(full_text)
    else:
        md.append("## Full Article")
        md.append("*(Article text could not be extracted. Visit source link above.)*")
    
    md.append("")
    md.append("---")
    md.append("")
    md.append("*Content scraped from public sources with attribution. Users assume all risk.*  ")
    md.append(f"*Auto-generated by [Perplexity News Tracker](https://github.com/myidkd1-coder/perplexity-news-tracker)*")

    (out_dir / filename).write_text("\n".join(md), encoding="utf-8")
    return out_dir / filename

def write_index(base_dir: Path, category: str):
    """Generate index.md with all article files and their titles."""
    cat_dir = base_dir / category
    if not cat_dir.exists():
        return
    
    files = sorted(cat_dir.glob("*.md"))
    # Exclude index.md itself
    files = [f for f in files if f.name != "index.md"]
    
    idx = []
    idx.append(f"# {category.upper()} News - {today_yyyy_mm_dd()}")
    idx.append("")
    idx.append(f"**Total Articles:** {len(files)}")
    idx.append("")
    
    for f in files:
        # Read first line (title) from each file
        try:
            first_line = f.read_text(encoding="utf-8").split("\n")[0]
            title = first_line.replace("# ", "").strip()
        except:
            title = f.stem
        
        rel = f.relative_to(base_dir)
        idx.append(f"- [{title}]({rel.as_posix()})")
    
    idx.append("")
    idx.append("---")
    idx.append(f"*Updated: {now_utc_iso()}*")
    
    (cat_dir / "index.md").write_text("\n".join(idx), encoding="utf-8")

def main():
    api_key = os.getenv("PERPLEXITY_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("❌ PERPLEXITY_API_KEY missing in environment.")

    day_dir = Path("news") / today_yyyy_mm_dd()
    state_path = Path("news") / ".state" / f"{today_yyyy_mm_dd()}.json"
    state = load_state(state_path)
    seen = set(state.get("seen", []))

    print(f"🚀 Starting news fetch for {today_yyyy_mm_dd()}\n")

    for category, description in CATEGORIES.items():
        print(f"📰 Category: {category.upper()}")
        
        # Get news items from Perplexity
        resp = perplexity_request(api_key, category, description)
        print(f"  API Status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"  ❌ Error: {resp.text[:300]}")
            continue

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        try:
            parsed = json.loads(content)
            items = parsed.get("items", [])
        except:
            print(f"  ⚠️  Failed to parse JSON response")
            continue

        print(f"  Found {len(items)} items")
        
        for i, item in enumerate(items, 1):
            url = (item.get("url") or "").strip()
            title = (item.get("title") or "").strip()
            
            dedupe_key = url or ("title:" + title)
            if dedupe_key in seen:
                print(f"  [{i}/5] ⏭️  Duplicate: {title[:50]}...")
                continue

            print(f"  [{i}/5] Processing: {title[:60]}...")
            
            # Scrape full article
            scraped = scrape_full_article(url)
            
            # Write article file
            fpath = write_post_file(day_dir, category, item, scraped)
            print(f"    ✅ Saved: {fpath.name}")
            
            seen.add(dedupe_key)
            
            # Polite delay between scrapes
            time.sleep(1)
        
        # Generate index for this category
        write_index(day_dir, category)
        print(f"  📋 Index updated\n")

    # Save state
    state["seen"] = sorted(seen)
    save_state(state_path, state)
    
    print("✨ All done!")

if __name__ == "__main__":
    main()
