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

    print(f"Generating image: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
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

    print(f"Saved to: {output_path}")
    return output_path


def batch_generate(prompt_file: str) -> list[str]:
    """Read prompts from a file (one per line) and generate images for each."""
    text = Path(prompt_file).read_text(encoding="utf-8")
    prompts = [line.strip() for line in text.splitlines() if line.strip()]

    if not prompts:
        print("No valid prompts found in the file.")
        return []

    print(f"Found {len(prompts)} prompts, starting batch generation...")
    results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}/{len(prompts)}]")
        try:
            path = generate_image(prompt)
            results.append(path)
        except Exception as e:
            print(f"Failed: {e}")

    print(f"\nDone. {len(results)}/{len(prompts)} images generated.")
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
