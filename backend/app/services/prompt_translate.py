import re

PHRASE_MAP = {
    "masterpiece": "杰作",
    "best quality": "最佳质量",
    "high quality": "高质量",
    "ultra detailed": "超细节",
    "extremely detailed": "极致细节",
    "photorealistic": "照片级写实",
    "cinematic lighting": "电影级打光",
    "dramatic lighting": "戏剧化光影",
    "soft lighting": "柔和光线",
    "studio lighting": "影棚打光",
    "depth of field": "景深",
    "sharp focus": "清晰对焦",
    "beautiful detailed eyes": "精致眼睛细节",
    "detailed face": "面部细节丰富",
    "looking at viewer": "看向观众",
    "full body": "全身",
    "upper body": "上半身",
    "close up": "近景",
    "1girl": "1个女孩",
    "1boy": "1个男孩",
    "solo": "单人",
    "portrait": "人像",
    "landscape": "风景",
    "anime style": "动漫风格",
    "official art": "官方艺术风",
    "illustration": "插画",
    "white background": "白色背景",
    "simple background": "简洁背景",
}

WORD_MAP = {
    "girl": "女孩",
    "boy": "男孩",
    "woman": "女性",
    "man": "男性",
    "solo": "单人",
    "smile": "微笑",
    "blush": "脸红",
    "long": "长",
    "short": "短",
    "hair": "头发",
    "eyes": "眼睛",
    "blue": "蓝色",
    "white": "白色",
    "black": "黑色",
    "red": "红色",
    "green": "绿色",
    "pink": "粉色",
    "brown": "棕色",
    "dress": "连衣裙",
    "skirt": "裙子",
    "shirt": "衬衫",
    "jacket": "夹克",
    "coat": "外套",
    "hat": "帽子",
    "ribbon": "丝带",
    "flower": "花",
    "night": "夜晚",
    "day": "白天",
    "sky": "天空",
    "cloud": "云",
    "city": "城市",
    "street": "街道",
    "room": "房间",
    "window": "窗户",
    "light": "光线",
    "background": "背景",
    "detailed": "细节",
    "quality": "质量",
    "beautiful": "美丽",
}


def _contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _translate_weighted_segment(segment: str) -> str:
    # Keep SD weight syntax stable, e.g. "(masterpiece:1.2)".
    match = re.fullmatch(r"(\(+)(.+?)(:\s*[\d\.]+)(\)+)", segment.strip())
    if not match:
        return segment
    prefix, core, weight, suffix = match.groups()
    return f"{prefix}{_translate_simple_segment(core)}{weight}{suffix}"


def _translate_simple_segment(segment: str) -> str:
    raw = segment.strip()
    if not raw:
        return raw

    lower = raw.lower()
    if lower in PHRASE_MAP:
        return PHRASE_MAP[lower]

    if _contains_chinese(raw):
        return raw

    tokens = re.split(r"(\s+|[_\-])", raw)
    translated: list[str] = []
    for token in tokens:
        normalized = token.strip().lower()
        if not normalized or token.isspace() or token in {"_", "-"}:
            translated.append(token)
            continue
        translated.append(WORD_MAP.get(normalized, token))
    return "".join(translated)


def translate_prompt_to_zh(prompt: str) -> str:
    text = prompt.strip()
    if not text:
        return ""
    if _contains_chinese(text):
        return text

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    translated_lines: list[str] = []
    for line in lines:
        parts = [part.strip() for part in line.split(",")]
        translated_parts = []
        for part in parts:
            if not part:
                continue
            weighted = _translate_weighted_segment(part)
            translated_parts.append(weighted if weighted != part else _translate_simple_segment(part))
        translated_lines.append("，".join(translated_parts))
    return "\n".join(translated_lines)
