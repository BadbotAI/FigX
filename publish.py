#!/usr/bin/env python3
"""
FigX — Publish a thread (or single tweet) to X/Twitter with images.

Usage:
    python3 publish.py thread.json
    python3 publish.py thread.json --dry-run
    python3 publish.py thread.json --config config.json

JSON format: see examples/thread.example.json
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path


def load_env():
    """Load credentials from .env in current working directory."""
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())
        return str(env_path)
    return None


def get_credentials():
    """Get X API credentials from environment variables."""
    required = [
        "X_API_KEY", "X_API_SECRET",
        "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET",
        "X_BEARER_TOKEN",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"[ERROR] Missing env vars: {', '.join(missing)}")
        print()
        print("Set them in .env (same directory) or as environment variables.")
        print("See .env.example for the required format.")
        sys.exit(1)
    return {k: os.environ[k] for k in required}


def load_config(config_path=None):
    """Load config.json for archive_dir and other settings."""
    if config_path and Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Try CWD
    cwd_config = Path.cwd() / "config.json"
    if cwd_config.exists():
        with open(cwd_config, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def validate_thread(thread_data, skip_image_check=False, max_tweets=25):
    """Pre-publish validation. Returns list of errors."""
    errors = []
    tweets = thread_data.get("tweets", [])
    img_dir = os.path.expanduser(thread_data.get("img_dir", ""))

    if not tweets:
        errors.append("No tweets in thread")
        return errors

    if len(tweets) > max_tweets:
        errors.append(f"Too many tweets: {len(tweets)} (max {max_tweets})")

    for i, tweet in enumerate(tweets, 1):
        text = tweet.get("text", "")
        images = tweet.get("images", [])

        # Character limit
        if len(text) > 280:
            errors.append(
                f"Tweet {i} [{tweet.get('role', '?')}]: "
                f"{len(text)} chars (max 280, over by {len(text) - 280})"
            )

        # Empty text
        if not text.strip():
            errors.append(f"Tweet {i}: empty text")

        # Image count
        if len(images) > 4:
            errors.append(f"Tweet {i}: {len(images)} images (max 4)")

        # Image files exist (skip in dry-run mode)
        if not skip_image_check:
            for img in images:
                img_path = os.path.join(img_dir, img)
                if not os.path.exists(img_path):
                    errors.append(f"Tweet {i}: image not found: {img_path}")

    return errors


def publish(thread_data, dry_run=False, config=None):
    """Publish thread to X. Returns first tweet ID on success."""
    config = config or {}
    tweets = thread_data.get("tweets", [])
    img_dir = os.path.expanduser(thread_data.get("img_dir", ""))
    topic = thread_data.get("topic", "unknown")
    max_tweets = config.get("thread", {}).get("max_tweets", 25)

    # Validate first
    errors = validate_thread(thread_data, skip_image_check=dry_run, max_tweets=max_tweets)
    if errors:
        print("[VALIDATION FAILED]")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # Single tweet mode: <=4 images, 1 tweet
    is_single = len(tweets) == 1
    mode = "single tweet" if is_single else f"thread ({len(tweets)} tweets)"
    print(f"[OK] Validation passed: {mode}, all <= 280 chars")

    if dry_run:
        print(f"\n[DRY RUN] Preview ({mode}):")
        for i, tweet in enumerate(tweets, 1):
            role = tweet.get("role", "?")
            text = tweet["text"]
            images = tweet.get("images", [])
            print(f"\n--- Tweet {i}/{len(tweets)} [{role}] ({len(text)} chars) ---")
            print(text)
            if images:
                print(f"  Images: {', '.join(images)}")
        print("\n[DRY RUN] No tweets posted.")
        return None

    # Auth (only needed for actual publishing)
    import tweepy
    creds = get_credentials()
    auth = tweepy.OAuth1UserHandler(
        creds["X_API_KEY"], creds["X_API_SECRET"],
        creds["X_ACCESS_TOKEN"], creds["X_ACCESS_TOKEN_SECRET"],
    )
    api_v1 = tweepy.API(auth)
    client = tweepy.Client(
        bearer_token=creds["X_BEARER_TOKEN"],
        consumer_key=creds["X_API_KEY"],
        consumer_secret=creds["X_API_SECRET"],
        access_token=creds["X_ACCESS_TOKEN"],
        access_token_secret=creds["X_ACCESS_TOKEN_SECRET"],
    )

    print(f"\n=== Publishing: {topic} ({mode}) ===\n")

    prev_tweet_id = None
    first_tweet_id = None

    for i, tweet in enumerate(tweets, 1):
        role = tweet.get("role", "?")
        text = tweet["text"]
        images = tweet.get("images", [])

        print(f"--- Tweet {i}/{len(tweets)} [{role}] ---")

        # Upload images via v1.1 API
        media_ids = []
        for img_name in images:
            img_path = os.path.join(img_dir, img_name)
            print(f"  Uploading {img_name}...", end=" ", flush=True)
            media = api_v1.media_upload(img_path)
            media_ids.append(media.media_id)
            print(f"media_id={media.media_id}")

        # Post tweet
        kwargs = {"text": text}
        if media_ids:
            kwargs["media_ids"] = media_ids
        if prev_tweet_id:
            kwargs["in_reply_to_tweet_id"] = prev_tweet_id

        print("  Posting...", end=" ", flush=True)

        try:
            response = client.create_tweet(**kwargs)
            tweet_id = response.data["id"]
        except Exception as e:
            error_str = str(e)
            if "403" in error_str:
                print(f"\n  [RETRY] 403 error, waiting 5s...")
                time.sleep(5)
                try:
                    response = client.create_tweet(**kwargs)
                    tweet_id = response.data["id"]
                except Exception as retry_err:
                    print(f"\n  [FAILED] Retry also failed: {retry_err}")
                    print("  Hint: X Free tier restricts programmatic replies.")
                    print("  Thread publishing may require Basic/Pro tier.")
                    raise
            else:
                raise

        prev_tweet_id = tweet_id
        if first_tweet_id is None:
            first_tweet_id = tweet_id

        url = f"https://x.com/i/status/{tweet_id}"
        print(f"OK! {url}")

        if i < len(tweets):
            time.sleep(2)

    thread_url = f"https://x.com/i/status/{first_tweet_id}"
    print(f"\n=== Published! ===")
    print(f"URL: {thread_url}")

    # Write published.log
    log_line = f"{datetime.now().isoformat()} | {topic} | {thread_url}\n"
    log_path = Path.cwd() / "published.log"
    with open(log_path, "a") as f:
        f.write(log_line)

    # Archive thread JSON
    archive_dir_name = config.get("output", {}).get("archive_dir", "./archive")
    archive_dir = Path(archive_dir_name)
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{topic}.json"
    thread_data["published_at"] = datetime.now().isoformat()
    thread_data["thread_url"] = thread_url
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(thread_data, f, ensure_ascii=False, indent=2)
    print(f"Archived: {archive_path}")

    return first_tweet_id


def main():
    parser = argparse.ArgumentParser(
        description="FigX — Publish a thread to X/Twitter from JSON"
    )
    parser.add_argument("json_file", help="Path to thread.json")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate and preview without posting"
    )
    parser.add_argument(
        "--config", default=None,
        help="Path to config.json (default: ./config.json)"
    )
    args = parser.parse_args()

    # Load env
    env_file = load_env()
    if env_file:
        print(f"[env] Loaded from {env_file}")
    else:
        print("[env] No .env found in current directory, using environment variables")

    # Load config
    config = load_config(args.config)

    # Load thread data
    with open(args.json_file, "r", encoding="utf-8") as f:
        thread_data = json.load(f)

    publish(thread_data, dry_run=args.dry_run, config=config)


if __name__ == "__main__":
    main()
