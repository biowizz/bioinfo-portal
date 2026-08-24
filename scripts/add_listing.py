#!/usr/bin/env python3
"""Paste a URL or raw text for a bioinformatics conference/job listing,
parse it into the site's YAML schema via the Claude API, let the user
review/edit the result, then write it to data/conferences/ or data/jobs/.

Usage:
    python scripts/add_listing.py --url "https://example.org/some-posting"
    python scripts/add_listing.py --text "paste the raw announcement text..."
    python scripts/add_listing.py               # interactive: paste text or a URL when prompted
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
MODEL = "claude-opus-5"
MAX_SOURCE_CHARS = 15000

FIELDS = [
    "type",
    "title",
    "organization",
    "location",
    "remote",
    "deadline",
    "start_date",
    "end_date",
    "tags",
    "source_url",
    "added_on",
    "description",
]

EXTRACTION_SYSTEM_PROMPT = """You extract structured listing data for a bioinformatics \
conferences & jobs website. You will be given raw text from a job posting or \
conference announcement.

Respond with ONLY a single JSON object — no markdown code fences, no commentary, \
no explanation before or after. The JSON object must have exactly these keys:

- type: the string "job" or "conference"
- title: the listing's title, as a plain string
- organization: the hiring org / conference organizer, as a plain string
- location: city/country, or "Remote" if fully remote, or null if unknown
- remote: true or false
- deadline: the application/abstract/registration deadline as "YYYY-MM-DD", or null if not stated
- start_date: for conferences, the start date as "YYYY-MM-DD", or null (always null for jobs)
- end_date: for conferences, the end date as "YYYY-MM-DD", or null (always null for jobs)
- tags: an array of 2-6 short lowercase-kebab-case tags (e.g. "genomics", "single-cell", "postdoc")
- source_url: the URL of the posting if one is present in the text, else null
- description: a plain 2-3 sentence summary of the listing, as a single string (no line breaks)

If a field cannot be determined from the text, use null (or [] for tags, or false for remote). \
Do not invent facts that aren't in the source text."""


def fetch_url_text(url: str) -> str:
    resp = requests.get(url, timeout=20, headers={"User-Agent": "bioinfo-portal-bot/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:MAX_SOURCE_CHARS]


def read_pasted_text() -> str:
    print("Paste the listing text below, then press Ctrl-D (or Ctrl-Z on Windows) when done:")
    return sys.stdin.read().strip()


def extract_listing(client, source_text: str) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": source_text}],
    )
    raw = "".join(block.text for block in response.content if block.type == "text").strip()
    raw = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        print("\nClaude's response wasn't valid JSON. Raw response:\n")
        print(raw)
        raise SystemExit(f"JSON parse error: {exc}")


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def build_filename(listing: dict) -> str:
    year_source = listing.get("deadline") or listing.get("start_date") or listing.get("added_on") or ""
    year_match = re.match(r"(\d{4})", str(year_source))
    year = year_match.group(1) if year_match else str(date.today().year)
    slug = slugify(listing.get("title", "untitled"))
    return f"{year}-{slug}.yaml"


def print_listing(listing: dict) -> None:
    print("\n--- Parsed listing ---")
    for field in FIELDS:
        print(f"  {field}: {listing.get(field)!r}")
    print("----------------------\n")


def review_and_edit(listing: dict) -> dict:
    while True:
        print_listing(listing)
        choice = input(
            "Press Enter to save, type a field name to edit it, or 'q' to abort: "
        ).strip()
        if choice == "":
            return listing
        if choice.lower() == "q":
            raise SystemExit("Aborted — nothing was saved.")
        if choice not in FIELDS:
            print(f"Unknown field {choice!r}. Valid fields: {', '.join(FIELDS)}")
            continue
        new_value = input(f"New value for {choice} (JSON, e.g. \"text\", true, [\"a\",\"b\"], null): ").strip()
        try:
            listing[choice] = json.loads(new_value)
        except json.JSONDecodeError:
            listing[choice] = new_value  # fall back to raw string


def write_yaml(listing: dict) -> Path:
    listing_type = listing.get("type")
    if listing_type not in ("job", "conference"):
        raise SystemExit(f"type must be 'job' or 'conference', got {listing_type!r}")

    subdir = "jobs" if listing_type == "job" else "conferences"
    out_dir = DATA_DIR / subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = build_filename(listing)
    out_path = out_dir / filename
    if out_path.exists():
        raise SystemExit(f"{out_path} already exists — refusing to overwrite.")

    ordered = {field: listing.get(field) for field in FIELDS}

    class LiteralStr(str):
        pass

    def literal_str_representer(dumper, data):
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")

    yaml.add_representer(LiteralStr, literal_str_representer)
    if ordered.get("description"):
        ordered["description"] = LiteralStr(str(ordered["description"]).strip() + "\n")

    with out_path.open("w") as f:
        yaml.dump(ordered, f, sort_keys=False, allow_unicode=True, default_flow_style=False)

    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--url", help="URL of the posting/announcement to fetch and parse")
    group.add_argument("--text", help="Raw text of the posting/announcement to parse")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")

    import os

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ANTHROPIC_API_KEY not set. Create a .env file in the repo root "
            "(see .env.example) with your Claude API key."
        )

    import anthropic

    client = anthropic.Anthropic()

    if args.url:
        print(f"Fetching {args.url} ...")
        source_text = fetch_url_text(args.url)
        source_url_hint = args.url
    elif args.text:
        source_text = args.text
        source_url_hint = None
    else:
        source_text = read_pasted_text()
        source_url_hint = None

    if not source_text:
        raise SystemExit("No text to parse.")

    print("Sending to Claude for extraction...")
    listing = extract_listing(client, source_text)

    listing["added_on"] = date.today().isoformat()
    if source_url_hint and not listing.get("source_url"):
        listing["source_url"] = source_url_hint

    listing = review_and_edit(listing)
    out_path = write_yaml(listing)
    print(f"Saved {out_path.relative_to(REPO_ROOT)}")
    print("Review the file, then git add/commit/push to trigger the site rebuild.")


if __name__ == "__main__":
    main()
