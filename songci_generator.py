"""Batch generate Song Ci poetry art images following the poetry-art-prompt template."""

import re
import time
import sys
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

API_URL = "https://api.pptoken.org/v1/images/generations"
API_KEY = os.getenv("PPTOKEN_API_KEY")
OUTPUT_DIR = Path("output/songci")
POEM_FILE = Path("宋词百首.md")


# ── Theme classification ──────────────────────────────────────────────

THEME_KEYWORDS = {
    "思乡怀人": ["故乡", "乡", "归", "家", "思", "愁", "梦", "忆", "旧", "故国", "江南", "天涯"],
    "爱情离别": ["相思", "情", "恨", "离", "别", "泪", "断肠", "鸳鸯", "相思", "红笺", "彩笺"],
    "边塞豪情": ["塞", "边", "将军", "战", "剑", "铁马", "戈", "弓", "射", "军", "胡虏"],
    "山水田园": ["山", "水", "江", "湖", "溪", "柳", "花", "月", "风", "竹", "荷", "桥", "舟", "渔"],
    "咏物言志": ["梅", "菊", "竹", "兰", "松", "鹤", "雁", "雪", "霜"],
    "羁旅愁思": ["客", "旅", "孤", "独", "寒", "暮", "残", "羁", "渡", "舟"],
    "咏史怀古": ["古", "昔", "六朝", "兴亡", "遗", "旧事", "英雄", "千古"],
    "哲理禅意": ["人生", "梦", "空", "无", "浮生", "逍遥", "风月"],
    "闺怨相思": ["闺", "妆", "帘", "楼", "屏", "绣", "钗", "镜", "罗裳"],
    "家国情怀": ["国", "臣", "社稷", "山河", "天下", "壮志", "报国"],
}

PATTERN_MAP = {
    "思乡怀人": {"main": "回纹、明月纹、柳条纹", "aux": "归雁纹、书信纹、落叶纹", "corner": "回纹"},
    "爱情离别": {"main": "缠枝花纹、双燕纹、红豆纹", "aux": "鸳鸯纹、桃花纹", "corner": "缠枝花纹"},
    "边塞豪情": {"main": "剑纹、旌旗纹、大漠纹", "aux": "铠甲纹、孤烟纹、长城剪影", "corner": "剑纹"},
    "山水田园": {"main": "山水纹、云纹、松纹", "aux": "水波纹、鹤纹、远山剪影", "corner": "云纹"},
    "咏物言志": {"main": "竹纹、梅纹、兰纹", "aux": "菊花纹、松纹、石纹", "corner": "竹纹"},
    "羁旅愁思": {"main": "水波纹、芦苇纹、夜月纹", "aux": "舟纹、渔火纹、寒寺塔影", "corner": "水波纹"},
    "咏史怀古": {"main": "龙纹、凤纹", "aux": "回纹、青铜纹、古钟纹", "corner": "回纹"},
    "哲理禅意": {"main": "太极纹、莲花纹", "aux": "八卦纹、流水纹、棋纹", "corner": "莲花纹"},
    "闺怨相思": {"main": "牡丹纹、蝴蝶纹", "aux": "绣花纹、纱帘纹、月光纹", "corner": "牡丹纹"},
    "家国情怀": {"main": "龙纹、山河纹", "aux": "旌旗纹、剑纹、长城剪影", "corner": "龙纹"},
}

EMOTION_MAP = {
    "思乡怀人": "惆怅、思乡、深情",
    "爱情离别": "哀婉、缱绻、依依不舍",
    "边塞豪情": "壮阔、豪迈、慷慨激昂",
    "山水田园": "淡雅、悠然、宁静",
    "咏物言志": "高洁、坚韧、清雅",
    "羁旅愁思": "孤寂、愁苦、漂泊",
    "咏史怀古": "苍凉、感慨、沉思",
    "哲理禅意": "超脱、恬淡、豁达",
    "闺怨相思": "幽怨、缠绵、哀愁",
    "家国情怀": "悲壮、激昂、忧愤",
}

ATMOSPHERE_MAP = {
    "思乡怀人": "月色如水、归思绵长的古典美学空间",
    "爱情离别": "花落人散、情深意切的古典美学空间",
    "边塞豪情": "大漠苍茫、壮阔雄浑的古典美学空间",
    "山水田园": "山水相依、天人合一的古典美学空间",
    "咏物言志": "清幽高雅、意境深远的古典美学空间",
    "羁旅愁思": "暮色苍茫、孤舟漂泊的古典美学空间",
    "咏史怀古": "岁月沧桑、兴亡如梦的古典美学空间",
    "哲理禅意": "空灵澄澈、物我两忘的古典美学空间",
    "闺怨相思": "深闺幽静、月下怀人的古典美学空间",
    "家国情怀": "山河壮丽、英雄气概的古典美学空间",
}


# ── Poem parsing ──────────────────────────────────────────────────────

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


def classify_theme(poem_body: str) -> str:
    scores = {}
    for theme, keywords in THEME_KEYWORDS.items():
        scores[theme] = sum(1 for kw in keywords if kw in poem_body)
    return max(scores, key=scores.get) if max(scores.values()) > 0 else "山水田园"


def extract_imagery(poem_body: str) -> list[str]:
    imagery_pool = [
        "明月", "残月", "落日", "斜阳", "东风", "西风", "春风", "秋风",
        "杨柳", "梧桐", "荷花", "梅花", "桃花", "菊花", "落花", "飞花",
        "青山", "远山", "大江", "春水", "流水", "寒烟", "暮云", "晓雾",
        "孤舟", "兰舟", "高楼", "小楼", "西楼", "画桥", "长亭",
        "鸿雁", "杜鹃", "黄鹂", "鸥鹭", "燕子", "鸳鸯",
        "栏杆", "珠帘", "纱窗", "罗裳", "青铜",
        "美酒", "箫鼓", "琵琶", "琴声",
        "霜雪", "烟雨", "细雨", "骤雨",
    ]
    found = [img for img in imagery_pool if img in poem_body]
    return found[:6] if found else ["古典意境"]


# ── Prompt generation ─────────────────────────────────────────────────

def build_prompt(poem: dict) -> str:
    theme = classify_theme(poem["body"])
    imagery = extract_imagery(poem["body"])
    pattern = PATTERN_MAP[theme]
    emotion = EMOTION_MAP[theme]
    atmosphere = ATMOSPHERE_MAP[theme]
    genre = "词"

    body_lines = poem["body"].replace("，", "，\n").replace("。", "。\n").splitlines()
    body_lines = [l.strip() for l in body_lines if l.strip()]

    return f"""生成一张**{poem['title']}意境图**，融合传统美学与诗意表达。

## 诗歌信息
- 标题：{poem['title']}
- 作者：宋·{poem['author']}
- 体裁：{genre}
- 主题：{theme}
- 核心意象：{"、".join(imagery)}
- 情感基调：{emotion}

## 整体布局要求
采用"诗画合一"的古典美学布局，中心对称构图，以诗句文字为核心，传统花纹为意境烘托。

## 画面元素
1. **标题与作者区**（置顶居中）
   - 标题"{poem['title']}"使用篆隶书法风格，玄墨色
   - 作者"宋·{poem['author']}"使用行楷风格，黛青色
   - 标题两侧配以对称{pattern['corner']}装饰

2. **诗句内容区**（居中偏上）
   诗句竖排右起：
{chr(10).join(body_lines)}
   - 字体为宋体风格，墨色
   - 行间点缀小型主题纹样

3. **装饰花纹系统**
   - 主要纹样：{pattern['main']}
   - 辅助纹样：{pattern['aux']}
   - 布局：四角角花、上下边饰、诗句间穿插，占画面15%以内

4. **背景与质感**
   - 仿古宣纸底色，米白色
   - 淡金色主题纹样水印（低透明度）
   - 宋代书画装裱风格边框

## 意境营造
- 留白：画面四周留白约1/8，营造空灵感
- 层次：前景诗句、中景花纹、远景背景形成空间感
- 韵律：花纹疏密与诗句节奏呼应
- 整体氛围：{atmosphere}

## 视觉风格
- 中国传统水墨画意境
- 古典书法与现代排版结合
- 温润淡雅的色调
- 高质量、高清、细腻

## 技术规格
- 输出格式：PNG
- 分辨率：2560×1440"""


# ── Image generation ──────────────────────────────────────────────────

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

    print(f"  Generating image...")
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

    print(f"  Saved: {output_path}")
    return output_path


# ── Main ──────────────────────────────────────────────────────────────

def main():
    if not API_KEY:
        print("Error: PPTOKEN_API_KEY not set in .env")
        sys.exit(1)

    poems = parse_poems(POEM_FILE)
    print(f"Parsed {len(poems)} poems from {POEM_FILE}")

    # Support resuming: skip already generated
    success = 0
    failed = 0
    skipped = 0

    for poem in poems:
        output_path = str(OUTPUT_DIR / f"songci_{poem['num']:03d}_{poem['title']}.png")
        if Path(output_path).exists():
            print(f"[{poem['num']:>3d}/{len(poems)}] SKIP (exists): {poem['title']} · {poem['author']}")
            skipped += 1
            continue

        print(f"\n[{poem['num']:>3d}/{len(poems)}] {poem['title']} · {poem['author']}")
        prompt = build_prompt(poem)

        try:
            generate_image(prompt, output_path)
            success += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1

        # Brief pause between requests
        if poem != poems[-1]:
            time.sleep(2)

    print(f"\n{'='*60}")
    print(f"Done! Generated: {success}, Skipped: {skipped}, Failed: {failed}")
    print(f"Output directory: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
