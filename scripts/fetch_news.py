#!/usr/bin/env python3
"""
Perplexity News Tracker
- 1 news item = 1 markdown file (slug from title)
- Creates category index.md for the day
- Stores only summary + source URLs (no full copyrighted article text)
"""

import os
import re
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import requests

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
    # Use UTC date to keep folder consistent across runners
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

    # JSON schema structured output supported via response_format. [web:74]
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
                    "Return ONLY valid JSON that matches the schema. "
                    "Do not include bracket citations like [1]. "
                    "Use real source URLs (one per item). "
                    "Summaries must be original and short (2-4 lines)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Category: {category}\n"
                    f"Task: Find top 5 latest {description}.\n"
                    f"Return 5 items with title, 2-4 line summary, publisher (if known), published_date (if known), and url."
                ),
            },
        ],
        "response_format": {"type": "json_schema", "json_schema": {"schema": schema}},
    }

    r = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    return r

def write_post_file(base_dir: Path, category: str, item: dict):
    title = item.get("title", "").strip()
    url = item.get("url", "").strip()
    summary = item.get("summary", "").strip()
    publisher = item.get("publisher", "").strip()
    published_date = item.get("published_date", "").strip()

    slug = slugify(title)
    # ensure uniqueness if same title repeats
    uniq = short_hash(url or title or now_utc_iso())
    filename = f"{slug}-{uniq}.md"

    out_dir = base_dir / category
    out_dir.mkdir(parents=True, exist_ok=True)

    md = []
    md.append(f"# {title}")
    md.append("")
    md.append(f"**Category:** {category}")
    md.append(f"**Generated (UTC):** {now_utc_iso()}")
    if published_date:
        md.append(f"**Published:** {published_date}")
    if publisher:
        md.append(f"**Publisher:** {publisher}")
    md.append("")
    md.append("## Summary")
    md.append(summary if summary else "(No summary returned.)")
    md.append("")
    md.append("## Source")
    md.append(f"- {url}" if url else "- (No URL returned.)")
    md.append("")
    md.append("*Auto-generated by Perplexity News Tracker*")

    (out_dir / filename).write_text("\n".join(md), encoding="utf-8")
    return out_dir / filename, url

def write_index(base_dir: Path, category: str, files: list[Path]):
    idx = []
    idx.append(f"# {category.upper()} Index")
    idx.append(f"**Date (UTC):** {today_yyyy_mm_dd()}")
    idx.append("")
    for f in sorted(files):
        rel = f.relative_to(base_dir)
        # Link text = file stem (pretty enough). Could be improved later.
        idx.append(f"- [{f.stem}]({rel.as_posix()})")
    idx.append("")
    (base_dir / category / "index.md").write_text("\n".join(idx), encoding="utf-8")

def main():
    api_key = os.getenv("PERPLEXITY_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("PERPLEXITY_API_KEY missing in GitHub Actions secrets.")

    day_dir = Path("news") / today_yyyy_mm_dd()
    state_path = Path("news") / ".state" / f"{today_yyyy_mm_dd()}.json"
    state = load_state(state_path)
    seen = set(state.get("seen", []))

    for category, description in CATEGORIES.items():
        print(f"Fetching: {category}")
        resp = perplexity_request(api_key, category, description)
        print(f"Status: {resp.status_code}")
        if resp.status_code != 200:
            # Fail fast so you see the real error in Actions logs.
            raise SystemExit(f"Perplexity API error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = json.loads(content)  # structured outputs should be valid JSON
        items = parsed.get("items", [])

        written_files = []
        for item in items:
            url = (item.get("url") or "").strip()
            # dedupe by url (preferred) else by title
            dedupe_key = url or ("title:" + (item.get("title") or ""))
            if dedupe_key in seen:
                continue

            fpath, saved_url = write_post_file(day_dir, category, item)
            written_files.append(fpath)
            seen.add(dedupe_key)
            print(f"  saved: {fpath}")

        # always generate index (even if no new files this run)
        write_index(day_dir, category, list((day_dir / category).glob("*.md")))

    state["seen"] = sorted(seen)
    save_state(state_path, state)
    print("Done.")

if __name__ == "__main__":
    main()
