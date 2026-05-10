"""Batch generate Song Ci images from prompts_all.txt.

Usage:
    source .venv/bin/activate
    python songci_generator.py              # Generate all
    python songci_generator.py --from 21    # Start from poem #21
    python songci_generator.py --only 25    # Only poem #25
"""

import re
import time
import sys
import base64
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

API_URL = "https://api.pptoken.org/v1/images/generations"
API_KEY = os.getenv("PPTOKEN_API_KEY")
OUTPUT_DIR = Path("output/songci")
PROMPTS_FILE = Path("prompts_all.txt")
POEM_FILE = Path("宋词百首.md")


def parse_poems(filepath: str) -> list[dict]:
    text = Path(filepath).read_text(encoding="utf-8")
    blocks = re.split(r"\n---\n", text)
    poems = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        m = re.match(r"##\s+(\d+)\.\s+(.+?)\s*·\s*(.+)", block)
        if not m:
            continue
        num = int(m.group(1))
        title = m.group(2).strip()
        author = m.group(3).strip()
        lines = []
        in_body = False
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("##"):
                continue
            if not in_body and line:
                in_body = True
            if in_body and line:
                lines.append(line)
        body = "\n".join(lines)
        if body:
            poems.append({"num": num, "title": title, "author": author, "body": body})
    return poems


def generate_image(prompt: str, output_path: str) -> str:
    payload = {
        "model": "gpt-image-2",
        "prompt": prompt,
        "n": 1,
        "size": "auto",
        "quality": "auto",
        "background": "auto",
        "output_format": "png",
        "moderation": "auto",
    }

    resp = requests.post(
        API_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=300,
    )
    resp.raise_for_status()

    data = resp.json()
    image_data = data["data"][0]

    if "b64_json" in image_data:
        img_bytes = base64.b64decode(image_data["b64_json"])
    elif "url" in image_data:
        img_bytes = requests.get(image_data["url"], timeout=60).content
    else:
        raise ValueError(f"Unexpected response format: {list(image_data.keys())}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(img_bytes)

    return output_path


def main():
    if not API_KEY:
        print("Error: PPTOKEN_API_KEY not set in .env")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Batch generate Song Ci images")
    parser.add_argument("--from", dest="from_num", type=int, default=None, help="Start from poem number")
    parser.add_argument("--only", type=int, default=None, help="Only generate specific poem number")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without generating images")
    args = parser.parse_args()

    # Read prompts
    prompts_text = PROMPTS_FILE.read_text(encoding="utf-8")
    prompts = prompts_text.split("===SEPARATOR===")
    prompts = [p.strip() for p in prompts if p.strip()]
    print(f"Loaded {len(prompts)} prompts from {PROMPTS_FILE}")

    # Parse poems for metadata (num, title)
    poems = parse_poems(POEM_FILE)
    poem_map = {p["num"]: p for p in poems}

    # Build task list
    tasks = []
    for i, prompt in enumerate(prompts):
        # Match prompt to poem number
        m = re.search(r"标题：(.+)", prompt)
        title = m.group(1).strip() if m else f"unknown_{i}"
        # Find matching poem
        poem = None
        for p in poems:
            if p["title"] == title:
                poem = p
                break
        if not poem:
            # Try by index
            if i < len(poems):
                poem = poems[i]
            else:
                continue

        if args.only and poem["num"] != args.only:
            continue
        if args.from_num and poem["num"] < args.from_num:
            continue

        tasks.append((poem, prompt))

    print(f"Will generate {len(tasks)} images\n")

    if args.dry_run:
        for poem, prompt in tasks:
            print(f"[{poem['num']:>3d}] {poem['title']} · {poem['author']}")
            print(f"  Prompt length: {len(prompt)} chars")
        return

    success = 0
    failed = 0
    skipped = 0

    for idx, (poem, prompt) in enumerate(tasks, 1):
        output_path = str(OUTPUT_DIR / f"songci_{poem['num']:03d}_{poem['title']}.png")

        if Path(output_path).exists():
            print(f"[{idx}/{len(tasks)}] SKIP (exists): {poem['title']} · {poem['author']}")
            skipped += 1
            continue

        print(f"[{idx}/{len(tasks)}] {poem['title']} · {poem['author']}")

        try:
            generate_image(prompt, output_path)
            print(f"  -> Saved: {output_path}")
            success += 1
        except Exception as e:
            print(f"  -> FAILED: {e}")
            failed += 1

        # Brief pause between requests
        if poem != tasks[-1][0]:
            time.sleep(2)

    print(f"\n{'='*60}")
    print(f"Done! Generated: {success}, Skipped: {skipped}, Failed: {failed}")
    print(f"Output: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
