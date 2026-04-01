"""Fallback product copy generation using rule-based templates (V5.5.0+)."""

from __future__ import annotations

import logging
from typing import List

from app.models.product import Product

logger = logging.getLogger(__name__)


def generate_fallback_product_copy(
    product: Product,
    selling_points: List[str],
    scene: str = "guide_chat",
    style: str = "natural",
    max_length: int = 50,
    count: int = 2,
) -> List[str]:
    """Generate fallback product copy when LLM output is unavailable."""
    logger.info(
        "[FALLBACK] Generating fallback copy: sku=%s scene=%s style=%s count=%s",
        product.sku,
        scene,
        style,
        count,
    )

    product_name = product.name
    tags = product.tags or []
    attributes = product.attributes or {}
    color = attributes.get("color", "") if attributes else ""

    key_points = selling_points[:2] if selling_points else []

    if scene == "guide_chat":
        messages = _generate_guide_chat_copy(product_name, color, key_points, style, max_length)
    elif scene == "moments":
        messages = _generate_moments_copy(product_name, color, key_points, style, max_length)
    else:
        messages = _generate_poster_copy(product_name, color, key_points, style, max_length)

    while len(messages) < count:
        generic = _generate_generic_copy(product_name, color, tags, max_length)
        if generic not in messages:
            messages.append(generic)

    final_messages = []
    for msg in messages[:count]:
        if len(msg) > max_length:
            msg = msg[: max_length - 1] + "…"
        final_messages.append(msg)

    logger.info("[FALLBACK] Generated %s fallback copies", len(final_messages))
    return final_messages


def _product_ref(product_name: str) -> str:
    if any(keyword in product_name for keyword in ("裤", "裙")):
        return "这条"
    if any(keyword in product_name for keyword in ("衬衫", "卫衣", "针织", "外套", "T恤", "羽绒")):
        return "这件"
    return "这款"


def _generate_guide_chat_copy(
    product_name: str,
    color: str,
    key_points: List[str],
    style: str,
    max_length: int,
) -> List[str]:
    """Generate guide-chat style fallback product copy."""
    messages: List[str] = []
    product_ref = _product_ref(product_name)
    color_desc = f"{color}这{product_ref[-1]}" if color else product_ref

    comfort_point = next((p for p in key_points if any(k in p for k in ("舒适", "柔软", "透气", "轻便"))), None)
    fit_point = next((p for p in key_points if any(k in p for k in ("版型", "显瘦", "宽松", "合身"))), None)
    scene_point = next((p for p in key_points if any(k in p for k in ("通勤", "约会", "日常", "搭配", "场景"))), None)

    if fit_point:
        msg1 = f"{color_desc}{fit_point}，你平时更喜欢合身一点还是宽松一点呀？"
    elif comfort_point:
        msg1 = f"{color_desc}{comfort_point}，如果你在意上身感受，我可以帮你细说下。"
    else:
        msg1 = f"{color_desc}整体还挺好搭的，你现在更在意尺码、版型还是搭配呀？"
    messages.append(msg1[:max_length])

    if scene_point:
        msg2 = f"{color_desc}放在{scene_point}这种场景里会比较顺，你想看下怎么搭吗？"
    elif fit_point:
        msg2 = f"{color_desc}上身会比较利落，你如果担心版型我可以帮你一起看。"
    else:
        msg2 = f"{color_desc}你平时这类单品一般穿什么尺码？我可以帮你对一下。"
    messages.append(msg2[:max_length])

    if not any("尺码" in message or "版型" in message for message in messages):
        msg3 = f"{color_desc}你平时这类单品怎么选尺码？我可以顺手帮你看看。"
        messages.append(msg3[:max_length])

    return messages[:3]


def _generate_moments_copy(
    product_name: str,
    color: str,
    key_points: List[str],
    style: str,
    max_length: int,
) -> List[str]:
    """Generate moments-style fallback product copy."""
    messages: List[str] = []
    base = f"{color}{product_name}" if color else product_name

    if key_points:
        point = key_points[0][:15]
        msg1 = f"{base}，{point}"
    else:
        msg1 = base
    messages.append(msg1[:max_length])

    msg2 = f"{base}，日常和通勤都比较好搭"
    messages.append(msg2[:max_length])
    return messages


def _generate_poster_copy(
    product_name: str,
    color: str,
    key_points: List[str],
    style: str,
    max_length: int,
) -> List[str]:
    """Generate poster-style fallback product copy."""
    messages: List[str] = []
    base = f"{color}{product_name}" if color else product_name

    if key_points:
        point = key_points[0][:12]
        messages.append(f"{base} | {point}"[:max_length])
    else:
        messages.append(base[:max_length])

    messages.append(f"{base} | 好穿也好搭"[:max_length])
    return messages


def _generate_generic_copy(
    product_name: str,
    color: str,
    tags: List[str],
    max_length: int,
) -> str:
    """Generate a generic backup copy."""
    product_ref = _product_ref(product_name)
    color_desc = f"{color}{product_name}" if color else product_name

    if any(tag in tags for tag in ("百搭", "通勤", "简约")):
        msg = f"{color_desc}整体比较百搭，{product_ref}日常穿会很省心。"
    elif any(tag in tags for tag in ("舒适", "轻便", "透气")):
        msg = f"{color_desc}穿着会比较舒服，{product_ref}日常上身压力不大。"
    else:
        msg = f"{color_desc}整体质感和搭配感都不错，{product_ref}挺值得看看。"

    return msg[:max_length]
