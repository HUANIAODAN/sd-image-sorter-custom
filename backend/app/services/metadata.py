from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, UnidentifiedImageError

from .prompt_translate import translate_prompt_to_zh
from .similarity import compute_dhash


def _decode_exif_value(value: object) -> str | None:
    if isinstance(value, bytes):
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                decoded = value.decode(encoding, errors="ignore").strip("\x00")
            except UnicodeDecodeError:
                continue
            if decoded:
                return decoded
        return None
    if isinstance(value, str):
        return value
    return None


def _collect_text_metadata(img: Image.Image) -> dict[str, str]:
    text_meta: dict[str, str] = {}
    for key, value in img.info.items():
        if isinstance(value, str):
            text_meta[str(key)] = value

    exif = img.getexif()
    if exif:
        for tag_id, value in exif.items():
            tag_name = str(ExifTags.TAGS.get(tag_id, tag_id))
            decoded = _decode_exif_value(value)
            if decoded:
                text_meta[tag_name] = decoded
    return text_meta


def _dedupe_keep_order(items: list[str]) -> list[str]:
    clean_items = [item.strip() for item in items if item and item.strip()]
    return list(dict.fromkeys(clean_items))


def _extract_loras_from_text(text: str) -> list[str]:
    matches = re.findall(r"<(?:lora|lyco):([^:>]+)(?::[^>]+)?>", text, flags=re.IGNORECASE)
    return _dedupe_keep_order(matches)


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _find_setting_value(settings_text: str, key: str) -> str:
    pattern = re.compile(
        rf"(?:^|, ){re.escape(key)}: (.*?)(?=(?:, [A-Za-z][A-Za-z0-9_ /()\-]*: )|$)",
        flags=re.DOTALL,
    )
    match = pattern.search(settings_text)
    return match.group(1).strip() if match else ""


def _parse_gen_params_line(params_line: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if not params_line:
        return result

    pairs: list[str] = []
    current: list[str] = []
    in_quotes = False
    for index, char in enumerate(params_line):
        if char == '"' and (index == 0 or params_line[index - 1] != "\\"):
            in_quotes = not in_quotes
            current.append(char)
            continue
        if char == "," and not in_quotes:
            remainder = params_line[index + 1 :]
            if re.match(r"^\s*[A-Za-z][A-Za-z0-9 _/\-]*:", remainder):
                chunk = "".join(current).strip()
                if chunk:
                    pairs.append(chunk)
                current = []
                continue
        current.append(char)

    trailing = "".join(current).strip()
    if trailing:
        pairs.append(trailing)

    for pair in pairs:
        match = re.match(r"^\s*([^:]+):\s*(.+)$", pair.strip())
        if not match:
            continue
        key = match.group(1).strip().lower().replace(" ", "_")
        value = match.group(2).strip()
        if key in {"steps", "clip_skip"}:
            result[key] = _to_int(value)
        elif key in {"cfg_scale", "denoising_strength", "hires_upscale"}:
            result[key] = _to_float(value)
        elif key == "seed":
            result[key] = value
        else:
            result[key] = value
    return result


def _parse_a1111_parameters(parameters: str, generator_source: str) -> dict[str, Any]:
    text = parameters.strip()
    if not text:
        return {}

    positive = text
    negative = ""
    settings_text = ""

    if "\nNegative prompt:" in text:
        positive, tail = text.split("\nNegative prompt:", 1)
        if "\nSteps:" in tail:
            negative, settings_tail = tail.split("\nSteps:", 1)
            settings_text = f"Steps: {settings_tail.strip()}"
        else:
            negative = tail
    elif "\nSteps:" in text:
        positive, settings_tail = text.split("\nSteps:", 1)
        settings_text = f"Steps: {settings_tail.strip()}"

    gen_params = _parse_gen_params_line(settings_text)
    loras = _extract_loras_from_text(positive) + _extract_loras_from_text(negative)
    addnet_loras = []
    for idx in range(1, 9):
        name = _find_setting_value(settings_text, f"AddNet Model {idx}")
        if name and name.lower() != "none":
            addnet_loras.append(name)

    return {
        "generator_source": generator_source,
        "positive_prompt": positive.strip(),
        "negative_prompt": negative.strip(),
        "checkpoint_name": str(gen_params.get("model") or gen_params.get("checkpoint") or ""),
        "vae_name": str(gen_params.get("vae") or ""),
        "seed": str(gen_params.get("seed") or ""),
        "lora_names": _dedupe_keep_order(loras + addnet_loras),
        "steps": _to_int(gen_params.get("steps")),
        "cfg_scale": _to_float(gen_params.get("cfg_scale")),
        "sampler": str(gen_params.get("sampler") or ""),
        "schedule_type": str(gen_params.get("schedule_type") or ""),
        "clip_skip": _to_int(gen_params.get("clip_skip")),
        "metadata": gen_params,
    }


def _extract_conditioning_text(graph: dict[str, dict], start_ref: object, seen: set[str] | None = None) -> list[str]:
    if seen is None:
        seen = set()
    if not isinstance(start_ref, list) or not start_ref:
        return []

    node_id = str(start_ref[0])
    if node_id in seen:
        return []
    seen.add(node_id)

    node = graph.get(node_id)
    if not isinstance(node, dict):
        return []

    inputs = node.get("inputs", {})
    class_type = str(node.get("class_type", ""))

    texts: list[str] = []
    if "CLIPTextEncode" in class_type and isinstance(inputs.get("text"), str):
        texts.append(inputs["text"].strip())

    for value in inputs.values():
        if isinstance(value, list) and value:
            texts.extend(_extract_conditioning_text(graph, value, seen))
    return texts


def _parse_comfy_prompt(prompt_json: str) -> dict[str, Any]:
    try:
        graph = json.loads(prompt_json)
    except json.JSONDecodeError:
        return {
            "generator_source": "ComfyUI",
            "positive_prompt": prompt_json.strip(),
            "negative_prompt": "",
            "checkpoint_name": "",
            "vae_name": "",
            "seed": "",
            "lora_names": [],
            "steps": None,
            "cfg_scale": None,
            "sampler": "",
            "schedule_type": "",
            "clip_skip": None,
            "metadata": {},
        }

    if not isinstance(graph, dict):
        return {
            "generator_source": "ComfyUI",
            "positive_prompt": "",
            "negative_prompt": "",
            "checkpoint_name": "",
            "vae_name": "",
            "seed": "",
            "lora_names": [],
            "steps": None,
            "cfg_scale": None,
            "sampler": "",
            "schedule_type": "",
            "clip_skip": None,
            "metadata": {},
        }

    positive_chunks: list[str] = []
    negative_chunks: list[str] = []
    checkpoint_name = ""
    vae_name = ""
    seed = ""
    lora_names: list[str] = []
    steps = None
    cfg_scale = None
    sampler = ""
    schedule_type = ""
    clip_skip = None

    for node in graph.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs", {})
        class_type = str(node.get("class_type", ""))

        if "KSampler" in class_type or "Sampler" in class_type:
            positive_chunks.extend(_extract_conditioning_text(graph, inputs.get("positive")))
            negative_chunks.extend(_extract_conditioning_text(graph, inputs.get("negative")))
            if seed in {"", None}:
                seed_value = inputs.get("seed") or inputs.get("noise_seed")
                if seed_value not in (None, ""):
                    seed = str(seed_value)
            if steps is None:
                steps = _to_int(inputs.get("steps"))
            if cfg_scale is None:
                cfg_scale = _to_float(inputs.get("cfg"))
            if not sampler:
                sampler = str(inputs.get("sampler_name") or inputs.get("sampler") or "")
            if not schedule_type:
                schedule_type = str(inputs.get("scheduler") or "")

        if "CheckpointLoader" in class_type and not checkpoint_name:
            value = inputs.get("ckpt_name") or inputs.get("model_name")
            if isinstance(value, str):
                checkpoint_name = value

        if class_type == "VAELoader" and not vae_name:
            value = inputs.get("vae_name")
            if isinstance(value, str):
                vae_name = value

        if "Lora" in class_type or "LoRA" in class_type:
            value = inputs.get("lora_name") or inputs.get("lora")
            if isinstance(value, str):
                lora_names.append(value)

        if class_type == "CLIPSetLastLayer" and clip_skip is None:
            clip_skip = _to_int(inputs.get("stop_at_clip_layer"))

    if not positive_chunks:
        for node in graph.values():
            if not isinstance(node, dict):
                continue
            if "CLIPTextEncode" in str(node.get("class_type", "")):
                text_value = node.get("inputs", {}).get("text")
                if isinstance(text_value, str) and text_value.strip():
                    positive_chunks.append(text_value.strip())

    positive = "\n\n".join(_dedupe_keep_order(positive_chunks))
    negative = "\n\n".join(_dedupe_keep_order(negative_chunks))

    return {
        "generator_source": "ComfyUI",
        "positive_prompt": positive,
        "negative_prompt": negative,
        "checkpoint_name": checkpoint_name,
        "vae_name": vae_name,
        "seed": seed,
        "lora_names": _dedupe_keep_order(lora_names + _extract_loras_from_text(positive)),
        "steps": steps,
        "cfg_scale": cfg_scale,
        "sampler": sampler,
        "schedule_type": schedule_type,
        "clip_skip": clip_skip,
        "metadata": {},
    }


def _parse_novelai_metadata(text_meta: dict[str, str]) -> dict[str, Any]:
    description = text_meta.get("Description", text_meta.get("description", "")).strip()
    comment_text = text_meta.get("Comment", text_meta.get("comment", "")).strip()
    negative = ""
    seed = ""
    loras: list[str] = []
    steps = None
    cfg_scale = None
    sampler = ""
    metadata: dict[str, Any] = {}

    if comment_text:
        try:
            comment_json = json.loads(comment_text)
        except json.JSONDecodeError:
            comment_json = {}

        if isinstance(comment_json, dict):
            metadata = comment_json
            negative = str(comment_json.get("uc", "")).strip()
            seed_value = comment_json.get("seed", "")
            if seed_value not in (None, ""):
                seed = str(seed_value)
            steps = _to_int(comment_json.get("steps"))
            cfg_scale = _to_float(comment_json.get("scale"))
            sampler = str(comment_json.get("sampler") or "")

    if description:
        loras = _extract_loras_from_text(description)

    return {
        "generator_source": "NovelAI",
        "positive_prompt": description,
        "negative_prompt": negative,
        "checkpoint_name": str(metadata.get("source") or metadata.get("model") or ""),
        "vae_name": "",
        "seed": seed,
        "lora_names": loras,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "sampler": sampler,
        "schedule_type": "",
        "clip_skip": None,
        "metadata": metadata,
    }


def _detect_generator_source(text_meta: dict[str, str]) -> str:
    lowered = {str(key).lower(): value for key, value in text_meta.items()}
    lower_blob = "\n".join(f"{k}:{v}" for k, v in lowered.items()).lower()
    if "prompt" in lowered or "workflow" in lowered:
        return "ComfyUI"
    if "novelai" in lower_blob:
        return "NovelAI"
    if "description" in lowered and "comment" in lowered:
        return "NovelAI"
    if "parameters" in lowered:
        if "forge" in lower_blob:
            return "Forge"
        return "WebUI"
    return "Unknown"


def _extract_generation_fields(text_meta: dict[str, str]) -> dict[str, Any]:
    lowered = {str(key).lower(): value for key, value in text_meta.items()}
    generator_source = _detect_generator_source(text_meta)

    if generator_source in {"WebUI", "Forge"}:
        return _parse_a1111_parameters(lowered.get("parameters", ""), generator_source)
    if generator_source == "ComfyUI":
        return _parse_comfy_prompt(lowered.get("prompt", lowered.get("workflow", "")))
    if generator_source == "NovelAI":
        return _parse_novelai_metadata(text_meta)

    user_comment = lowered.get("usercomment", "")
    if user_comment and ("Negative prompt:" in user_comment or "Steps:" in user_comment):
        return _parse_a1111_parameters(user_comment.replace("Negative prompt:", "\nNegative prompt:"), "WebUI")

    return {
        "generator_source": "Unknown",
        "positive_prompt": "",
        "negative_prompt": "",
        "checkpoint_name": "",
        "vae_name": "",
        "seed": "",
        "lora_names": [],
        "steps": None,
        "cfg_scale": None,
        "sampler": "",
        "schedule_type": "",
        "clip_skip": None,
        "metadata": {},
    }


def _infer_content_rating(positive_prompt: str, negative_prompt: str) -> str:
    blob = f"{positive_prompt} {negative_prompt}".lower()
    if any(token in blob for token in ("explicit", "nsfw", "sex", "nude", "nipples", "pussy", "penis")):
        return "explicit"
    if any(token in blob for token in ("questionable", "revealing", "suggestive", "underwear", "lingerie")):
        return "questionable"
    if any(token in blob for token in ("sensitive", "bikini", "swimsuit", "bra", "panties")):
        return "sensitive"
    return "unknown"


def parse_image_file(file_path: Path) -> dict[str, Any]:
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            text_meta = _collect_text_metadata(img)
            generation = _extract_generation_fields(text_meta)
            positive_prompt = generation.get("positive_prompt", "")
            negative_prompt = generation.get("negative_prompt", "")
            positive_prompt_zh = translate_prompt_to_zh(positive_prompt) if positive_prompt else ""
            phash = compute_dhash(file_path)
    except (UnidentifiedImageError, OSError):
        width, height = None, None
        text_meta = {}
        generation = {
            "generator_source": "Unknown",
            "positive_prompt": "",
            "negative_prompt": "",
            "checkpoint_name": "",
            "vae_name": "",
            "seed": "",
            "lora_names": [],
            "steps": None,
            "cfg_scale": None,
            "sampler": "",
            "schedule_type": "",
            "clip_skip": None,
            "metadata": {},
        }
        positive_prompt = ""
        negative_prompt = ""
        positive_prompt_zh = ""
        phash = ""

    stat = file_path.stat()
    return {
        "name": file_path.name,
        "ext": file_path.suffix.lower(),
        "width": width,
        "height": height,
        "size_bytes": int(stat.st_size),
        "mtime": float(stat.st_mtime),
        "generator_source": generation.get("generator_source", "Unknown"),
        "positive_prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "positive_prompt_zh": positive_prompt_zh,
        "checkpoint_name": generation.get("checkpoint_name", ""),
        "lora_names": _dedupe_keep_order(list(generation.get("lora_names", []))),
        "vae_name": generation.get("vae_name", ""),
        "seed": generation.get("seed", ""),
        "steps": generation.get("steps"),
        "cfg_scale": generation.get("cfg_scale"),
        "sampler": generation.get("sampler", ""),
        "schedule_type": generation.get("schedule_type", ""),
        "clip_skip": generation.get("clip_skip"),
        "content_rating": _infer_content_rating(positive_prompt, negative_prompt),
        "phash": phash,
        "metadata": {
            "raw": text_meta,
            "parsed": generation.get("metadata", {}),
        },
    }


def extract_metadata(file_path: Path) -> dict[str, Any]:
    parsed = parse_image_file(file_path)
    return {
        **parsed,
        "lora_names": ", ".join(parsed["lora_names"]),
    }
