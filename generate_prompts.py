"""Generate Song Ci image prompts following the poetry-art-prompt template.

Usage:
    python generate_prompts.py          # Generate all 100 prompts to prompts_all.txt
    python generate_prompts.py --from 21 # Start from poem #21
    python generate_prompts.py --only 25 # Only generate poem #25
"""

import re
import argparse
from pathlib import Path

POEM_FILE = Path("宋词百首.md")
OUTPUT_FILE = Path("prompts_all.txt")

# ── Theme classification (weighted keywords) ──────────────────────────

THEME_RULES = [
    # (theme, weight, keywords)
    ("边塞豪情", 3, ["塞下", "边声", "将军", "铁马", "燕然", "胡虏", "征夫", "射天狼",
                       "战", "弓如霹雳", "剑吼", "长缨", "天骄"]),
    ("家国情怀", 3, ["故国", "家国", "山河", "亡国", "臣虏", "辞庙", "社稷", "天下",
                       "报国", "靖康", "旧山河", "宫娥", "干戈", "风阁龙楼"]),
    ("咏史怀古", 2, ["六朝", "兴亡", "千古", "英雄", "遗曲", "后庭", "商女", "赤壁",
                       "周郎", "风流人物", "旧事", "繁华竞逐"]),
    ("咏物言志", 2, ["咏梅", "暗香", "疏影", "零落成泥", "高洁", "簪花", "倒著冠",
                       "冷眼看", "不争春", "一任群芳妒"]),
    ("哲理禅意", 1, ["人生如梦", "一蓑烟雨", "也无风雨", "此身非我有", "江海寄",
                       "营营", "浮生", "梦", "空", "无常"]),
    ("爱情离别", 2, ["相思", "离愁", "别", "泪眼", "执手", "残月", "杨柳岸", "彩笺",
                       "尺素", "鸳鸯", "红豆", "双燕", "离恨", "断肠", "衣带渐宽",
                       "不负相思", "两情久长", "鹊桥"]),
    ("闺怨相思", 2, ["深院", "珠帘", "罗幕", "妆楼", "绣", "钗", "罗裳", "屏风",
                       "秋千", "闺", "帘栊", "纱窗", "牡丹", "蝴蝶"]),
    ("羁旅愁思", 2, ["羁旅", "客", "孤馆", "征辔", "漂泊", "淹留", "孤城", "万里",
                       "天涯", "游子", "登高", "危楼", "归思", "乡关"]),
    ("思乡怀人", 1, ["故乡", "乡", "归", "家万里", "思", "忆旧", "梦中", "故人",
                       "明月楼", "雁去", "望故乡"]),
    ("山水田园", 1, ["西湖", "溪", "柳", "荷", "桂子", "钓叟", "菱歌", "田园",
                       "箫鼓", "渔", "春色", "秋色", "山水"]),
]

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
    scores: dict[str, float] = {}
    for theme, weight, keywords in THEME_RULES:
        scores[theme] = sum(weight for kw in keywords if kw in poem_body)
    if max(scores.values()) == 0:
        return "山水田园"
    return max(scores, key=scores.get)


def extract_imagery(poem_body: str) -> list[str]:
    pool = [
        "明月", "残月", "缺月", "落日", "斜阳", "斜照", "东风", "西风", "春风", "秋风", "晓风",
        "杨柳", "梧桐", "荷花", "梅花", "桃花", "菊花", "落花", "飞花", "残红", "乱红",
        "青山", "远山", "春山", "大江", "长江", "春水", "流水", "寒烟", "暮云", "晓雾",
        "孤舟", "兰舟", "征棹", "高楼", "小楼", "西楼", "画桥", "长亭",
        "鸿雁", "杜鹃", "黄鹂", "鸥鹭", "燕子", "鸳鸯", "孤鸿",
        "栏杆", "珠帘", "罗幕", "纱窗", "罗裳",
        "箫鼓", "琵琶", "琴声", "羌管",
        "霜雪", "烟雨", "细雨", "骤雨", "潇潇暮雨",
        "雕栏玉砌", "琼楼玉宇", "赤壁", "寒鸦", "飞絮",
    ]
    found = [img for img in pool if img in poem_body]
    return found[:6] if found else ["古典意境"]


def generate_background(poem: dict, theme: str, imagery: list[str]) -> dict:
    """Generate theme-aware background style."""
    body = poem["body"]
    img_set = set(imagery)

    # Base theme backgrounds
    bg_map = {
        "思乡怀人": {
            "base": "月白色宣纸底色",
            "watermark": "淡银色",
            "border": "素雅宋代装裱风格边框",
            "texture": "带有淡淡月晕光泽的纸质肌理",
        },
        "爱情离别": {
            "base": "藕粉色宣纸底色",
            "watermark": "淡玫金色",
            "border": "精致宋代装裱风格边框",
            "texture": "带有花瓣飘落痕迹的柔和纸质肌理",
        },
        "边塞豪情": {
            "base": "灰褐色粗纸底色",
            "watermark": "暗金色",
            "border": "厚重大气宋代装裱风格边框",
            "texture": "带有风沙磨砺感的粗粝纸质肌理",
        },
        "山水田园": {
            "base": "淡青白色宣纸底色",
            "watermark": "淡翠金色",
            "border": "清新宋代装裱风格边框",
            "texture": "带有山水晕染痕迹的清新纸质肌理",
        },
        "咏物言志": {
            "base": "素白色宣纸底色",
            "watermark": "淡墨色",
            "border": "简洁宋代装裱风格边框",
            "texture": "带有淡雅水墨渲染的洁净纸质肌理",
        },
        "羁旅愁思": {
            "base": "暮灰色宣纸底色",
            "watermark": "淡青灰色",
            "border": "素朴宋代装裱风格边框",
            "texture": "带有烟雨浸润感的朦胧纸质肌理",
        },
        "咏史怀古": {
            "base": "古铜色宣纸底色",
            "watermark": "暗金色",
            "border": "古朴厚重宋代装裱风格边框",
            "texture": "带有岁月斑驳痕迹的古旧纸质肌理",
        },
        "哲理禅意": {
            "base": "淡墨灰色宣纸底色",
            "watermark": "银灰色",
            "border": "极简宋代装裱风格边框",
            "texture": "带有水墨氤氲的空灵纸质肌理",
        },
        "闺怨相思": {
            "base": "淡紫粉色宣纸底色",
            "watermark": "淡藕金色",
            "border": "柔美宋代装裱风格边框",
            "texture": "带有纱帘透光感的朦胧纸质肌理",
        },
        "家国情怀": {
            "base": "深米色宣纸底色",
            "watermark": "赤金色",
            "border": "庄重宋代装裱风格边框",
            "texture": "带有历史厚重感的沉稳纸质肌理",
        },
    }

    bg = bg_map[theme].copy()

    # Fine-tune based on specific imagery
    if any(x in img_set for x in ["明月", "残月", "缺月"]):
        bg["base"] = "月白色宣纸底色"
        bg["watermark"] = "银蓝色"
        bg["texture"] = "带有月华流淌光泽的冷调纸质肌理"
    elif any(x in img_set for x in ["落日", "斜阳", "斜照"]):
        bg["base"] = "暖橘色宣纸底色"
        bg["watermark"] = "琥珀金色"
        bg["texture"] = "带有夕阳余晖暖调的纸质肌理"
    elif any(x in img_set for x in ["霜雪"]):
        bg["base"] = "冷白色宣纸底色"
        bg["watermark"] = "冰蓝色"
        bg["texture"] = "带有霜雪清冽质感的冷调纸质肌理"
    elif any(x in img_set for x in ["烟雨", "细雨", "骤雨", "潇潇暮雨"]):
        bg["base"] = "烟青色宣纸底色"
        bg["watermark"] = "淡青灰色"
        bg["texture"] = "带有雨雾浸润感的湿润纸质肌理"
    elif "梅花" in img_set:
        bg["base"] = "淡雪青色宣纸底色"
        bg["watermark"] = "冰粉色"
        bg["texture"] = "带有寒梅疏影的清冷纸质肌理"
    elif "荷花" in img_set:
        bg["base"] = "淡碧绿色宣纸底色"
        bg["watermark"] = "翠金色"
        bg["texture"] = "带有荷叶清露感的润泽纸质肌理"
    elif "桃花" in img_set:
        bg["base"] = "淡桃粉色宣纸底色"
        bg["watermark"] = "暖玫金色"
        bg["texture"] = "带有春花飘零痕迹的柔美纸质肌理"
    elif "梧桐" in img_set:
        bg["base"] = "深秋褐色宣纸底色"
        bg["watermark"] = "暗金色"
        bg["texture"] = "带有秋叶飘零的萧瑟纸质肌理"

    return bg


def generate_atmosphere(poem: dict, theme: str, imagery: list[str]) -> str:
    """Generate a poem-specific atmosphere description."""
    img_str = "、".join(imagery[:4])
    author = poem["author"]
    title = poem["title"]
    body = poem["body"]

    # Author-specific context
    author_ctx = ""
    if author == "李煜":
        author_ctx = "南唐后主的亡国之痛与故国之思在字里行间流淌"
    elif author == "苏轼":
        author_ctx = "东坡词中旷达超脱的人生态度跃然纸上"
    elif author == "李清照":
        author_ctx = "易安居士的婉约才情与身世之感交织其中"
    elif author == "辛弃疾":
        author_ctx = "稼轩词中壮志难酬的慷慨悲凉贯穿始终"
    elif author == "柳永":
        author_ctx = "柳词缠绵悱恻的离愁别绪弥漫全篇"
    elif author == "秦观":
        author_ctx = "少游词中凄美婉约的深情令人动容"
    elif author == "陆游":
        author_ctx = "放翁词中报国无门的悲愤与深情交织"
    elif author == "岳飞":
        author_ctx = "岳将军精忠报国的壮志豪情激荡人心"

    atmosphere_templates = {
        "思乡怀人": f"以{img_str}为核心意象，{author_ctx}，月色如水、归思绵长的古典美学空间",
        "爱情离别": f"以{img_str}为核心意象，{author_ctx}，花落人散、情深意切的古典美学空间",
        "边塞豪情": f"以{img_str}为核心意象，{author_ctx}，大漠苍茫、壮阔雄浑的古典美学空间",
        "山水田园": f"以{img_str}为核心意象，{author_ctx}，山水相依、天人合一的古典美学空间",
        "咏物言志": f"以{img_str}为核心意象，{author_ctx}，清幽高雅、意境深远的古典美学空间",
        "羁旅愁思": f"以{img_str}为核心意象，{author_ctx}，暮色苍茫、孤舟漂泊的古典美学空间",
        "咏史怀古": f"以{img_str}为核心意象，{author_ctx}，岁月沧桑、兴亡如梦的古典美学空间",
        "哲理禅意": f"以{img_str}为核心意象，{author_ctx}，空灵澄澈、物我两忘的古典美学空间",
        "闺怨相思": f"以{img_str}为核心意象，{author_ctx}，深闺幽静、月下怀人的古典美学空间",
        "家国情怀": f"以{img_str}为核心意象，{author_ctx}，山河壮丽、英雄气概的古典美学空间",
    }
    return atmosphere_templates.get(theme, atmosphere_templates["山水田园"])


def build_prompt_chatgpt(poem: dict) -> str:
    theme = classify_theme(poem["body"])
    imagery = extract_imagery(poem["body"])
    pattern = PATTERN_MAP[theme]
    atmosphere = generate_atmosphere(poem, theme, imagery)
    bg = generate_background(poem, theme, imagery)

    return f"""请生成一张宋词意境图，要求如下：

**诗词信息**
- 词牌名：{poem['title']}
- 作者：{poem['author']}（宋）

**词作全文**
{poem['body']}

**画面设计要求**

1. 整体风格：中国传统水墨画意境，诗画合一，温润淡雅
2. 构图：中心对称，以诗句文字为核心，传统花纹为意境烘托
3. 标题区（置顶居中）：词牌名"{poem['title']}"用篆隶书法风格、玄墨色；作者"{poem['author']}"用行楷风格、黛青色；两侧配{pattern['corner']}装饰
4. 诗句区（居中偏上）：词句竖排右起排列，宋体墨色
5. 装饰花纹：主要纹样{pattern['main']}，辅助纹样{pattern['aux']}，用于四角角花、边饰、诗句间穿插（占画面15%以内）
6. 背景：{bg['base']}，{bg['watermark']}主题纹样水印（低透明度），{bg['texture']}，{bg['border']}
7. 意境氛围：{atmosphere}
8. 画面四周留白约1/8，前景诗句、中景花纹、远景背景形成层次感

请直接生成这张意境图。"""


def build_prompt(poem: dict) -> str:
    theme = classify_theme(poem["body"])
    imagery = extract_imagery(poem["body"])
    pattern = PATTERN_MAP[theme]
    atmosphere = generate_atmosphere(poem, theme, imagery)
    bg = generate_background(poem, theme, imagery)

    body_lines = poem["body"].replace("，", "，\n").replace("。", "。\n").splitlines()
    body_lines = [l.strip() for l in body_lines if l.strip()]

    return f"""生成一张**{poem['title']}意境图**，融合传统美学与诗意表达。

## 诗歌信息
- 标题：{poem['title']}
- 作者：宋·{poem['author']}
- 体裁：词
- 主题：{theme}
- 核心意象：{"、".join(imagery)}
- 情感基调：{theme}的深沉韵致

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
   - {bg['base']}
   - {bg['watermark']}主题纹样水印（低透明度）
   - {bg['texture']}
   - {bg['border']}

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


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_num", type=int, default=None)
    parser.add_argument("--only", type=int, default=None)
    parser.add_argument("--format", choices=["api", "chatgpt"], default="api",
                        help="Output format: api (SEPARATOR delimited) or chatgpt (markdown)")
    args = parser.parse_args()

    poems = parse_poems(POEM_FILE)
    print(f"Parsed {len(poems)} poems")

    if args.only:
        poems = [p for p in poems if p["num"] == args.only]
    elif args.from_num:
        poems = [p for p in poems if p["num"] >= args.from_num]

    print(f"Generating prompts for {len(poems)} poems (format: {args.format})...")

    build_fn = build_prompt_chatgpt if args.format == "chatgpt" else build_prompt
    results = []
    for poem in poems:
        prompt = build_fn(poem)
        results.append(prompt)
        print(f"  [{poem['num']:>3d}] {poem['title']} · {poem['author']} -> {classify_theme(poem['body'])}")

    if args.format == "chatgpt":
        output = "\n\n---\n\n".join(results)
        out_file = Path("chatgpt_prompts.md")
    else:
        output = "\n===SEPARATOR===\n".join(results)
        out_file = OUTPUT_FILE

    out_file.write_text(output, encoding="utf-8")
    print(f"\nSaved {len(results)} prompts to {out_file}")


if __name__ == "__main__":
    main()
