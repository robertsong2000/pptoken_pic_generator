import re
import time
import requests
import sys
import base64
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

API_URL = "https://api.pptoken.org/v1/images/generations"
API_KEY = os.getenv("PPTOKEN_API_KEY")
OUTPUT_DIR = Path("output")


def extract_title(prompt: str, index: int) -> str:
    """Extract a descriptive filename from the prompt, fallback to index."""
    # Priority 1: explicit "# 标题: XXX" or "# 标题:XXX"
    first_line = prompt.strip().splitlines()[0]
    m = re.match(r"#\s*标题\s*[：:]\s*(.+)", first_line)
    if m:
        return m.group(1).strip().replace(" ", "_")[:40]
    # Priority 2: "标题：XXX" or "标题:XXX"
    m = re.search(r"标题[：:]\s*(.+?)[\n\r]", prompt)
    if m:
        return m.group(1).strip().replace(" ", "_")[:40]
    # Priority 3: "**XXX**" bold title
    m = re.search(r"\*\*(.+?)\*\*", prompt)
    if m:
        return m.group(1).strip().replace(" ", "_")[:40]
    # Priority 4: extract topic from "描绘XXX的" or "depicting XXX"
    m = re.search(r"(?:描绘|描写|展示|呈现)\s*[，,]?\s*(.{2,20}?)[，,、的]", prompt)
    if m:
        return re.sub(r"[^\w一-鿿·]", "_", m.group(1).strip())[:40].strip("_")
    return f"prompt_{index:03d}"


def generate_image(prompt: str, output_path: str | None = None) -> str:
    """Generate an image from a text prompt and save it locally."""
    OUTPUT_DIR.mkdir(exist_ok=True)

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

    print(f"  Generating...")
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

    if output_path is None:
        output_path = str(OUTPUT_DIR / f"{hash(prompt) & 0xFFFFFFFF:08x}.png")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(img_bytes)

    print(f"  Saved: {output_path}")
    return output_path


def batch_generate(prompt_file: str) -> list[str]:
    """Read prompts from a file and generate images for each.
    Supports SEPARATOR, ---, or newline-delimited prompts.
    """
    text = Path(prompt_file).read_text(encoding="utf-8")

    # Try SEPARATOR or --- first, fallback to line-by-line
    if "===SEPARATOR===" in text:
        prompts = [p.strip() for p in text.split("===SEPARATOR===") if p.strip()]
    elif "\n---\n" in text:
        prompts = [p.strip() for p in text.split("\n---\n") if p.strip()]
    else:
        prompts = [line.strip() for line in text.splitlines() if line.strip()]

    if not prompts:
        print("No valid prompts found in the file.")
        return []

    # Output directory named after the input file
    stem = Path(prompt_file).stem
    out_dir = OUTPUT_DIR / stem
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(prompts)} prompts, saving to {out_dir}/")
    print(f"Already generated: {len(list(out_dir.glob('*.png')))}")
    results = []
    success = 0
    failed = 0
    skipped = 0

    for i, prompt in enumerate(prompts, 1):
        title = extract_title(prompt, i)
        output_path = str(out_dir / f"{i:02d}_{title}.png")

        if Path(output_path).exists():
            print(f"[{i}/{len(prompts)}] SKIP (exists): {title}")
            skipped += 1
            continue

        print(f"[{i}/{len(prompts)}] {title}")
        try:
            generate_image(prompt, output_path)
            success += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1

        if prompt != prompts[-1]:
            time.sleep(2)

    print(f"\nDone. Success: {success}, Skipped: {skipped}, Failed: {failed}")
    print(f"Output: {out_dir.resolve()}")
    return results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if Path(arg).is_file():
            batch_generate(arg)
        else:
            generate_image(" ".join(sys.argv[1:]))
    else:
        generate_image("生成一张猫的图")
