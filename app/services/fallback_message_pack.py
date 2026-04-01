"""Fallback message pack generation with deterministic rotation (V5.6.0+)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.models.product import Product
from app.services.strategy_rotation import (
    MESSAGE_STRATEGY_ASK_CONCERN,
    MESSAGE_STRATEGY_ASK_SIZE,
    MESSAGE_STRATEGY_REASSURE_COMFORT,
    MESSAGE_STRATEGY_SCENE_RELATE,
    MESSAGE_STRATEGY_SOFT_CHECK,
    select_message_variant,
    select_strategies_for_pack,
)

logger = logging.getLogger(__name__)


def generate_fallback_message_pack(
    product: Product,
    intent_level: str,
    recommended_action: str,
    behavior_summary: Optional[Dict] = None,
    rotation_key: int = 0,
    max_length: int = 45,
    min_count: int = 3,
) -> List[dict]:
    """Generate a deterministic fallback message pack when LLM output is unavailable."""
    logger.info(
        "[FALLBACK] Generating fallback message pack: sku=%s intent=%s action=%s rotation_key=%s",
        product.sku,
        intent_level,
        recommended_action,
        rotation_key,
    )

    product_name = product.name
    tags = product.tags or []
    attributes = product.attributes or {}
    color = attributes.get("color", "") if attributes else ""
    scene = attributes.get("scene", "") if attributes else ""

    behavior_context = _extract_behavior_context(behavior_summary)

    strategies = select_strategies_for_pack(
        intent_level=intent_level,
        recommended_action=recommended_action,
        rotation_key=rotation_key,
        min_count=min_count,
    )

    messages = []
    for i, (strategy, strategy_desc) in enumerate(strategies):
        variant_idx = select_message_variant(strategy, rotation_key + i, variant_count=3)
        message = _generate_message_by_strategy(
            strategy=strategy,
            product_name=product_name,
            color=color,
            scene=scene,
            tags=tags,
            behavior_context=behavior_context,
            intent_level=intent_level,
            variant_idx=variant_idx,
            max_length=max_length,
        )
        messages.append(
            {
                "type": "primary" if i == 0 else "alternative",
                "strategy": strategy_desc,
                "message": message,
            }
        )

    logger.info("[FALLBACK] Generated %s fallback messages", len(messages))
    return messages


def _extract_behavior_context(behavior_summary: Optional[Dict]) -> Dict[str, Any]:
    """Extract reusable behavior context for fallback message generation."""
    if not behavior_summary:
        return {}

    visit_count = behavior_summary.get("visit_count", 0)
    avg_stay = behavior_summary.get("avg_stay_seconds", 0)
    has_favorite = behavior_summary.get("has_favorite", False)
    has_enter_buy_page = behavior_summary.get("has_enter_buy_page", False)

    return {
        "visit_count": visit_count,
        "avg_stay": avg_stay,
        "has_favorite": has_favorite,
        "has_enter_buy_page": has_enter_buy_page,
        "has_multiple_visits": visit_count >= 2,
        "has_long_stay": avg_stay >= 30,
    }


def _generate_message_by_strategy(
    strategy: str,
    product_name: str,
    color: str,
    scene: str,
    tags: List[str],
    behavior_context: Dict[str, Any],
    intent_level: str,
    variant_idx: int,
    max_length: int,
) -> str:
    """Generate a single fallback message by strategy."""
    if strategy == MESSAGE_STRATEGY_ASK_CONCERN:
        return _generate_ask_concern_message(
            product_name, color, behavior_context, variant_idx, max_length
        )
    if strategy == MESSAGE_STRATEGY_ASK_SIZE:
        return _generate_ask_size_message(
            product_name, color, behavior_context, variant_idx, max_length
        )
    if strategy == MESSAGE_STRATEGY_REASSURE_COMFORT:
        return _generate_reassure_comfort_message(
            product_name, color, tags, behavior_context, variant_idx, max_length
        )
    if strategy == MESSAGE_STRATEGY_SCENE_RELATE:
        return _generate_scene_relate_message(
            product_name, color, scene, behavior_context, variant_idx, max_length
        )
    return _generate_soft_check_message(
        product_name, color, behavior_context, variant_idx, max_length
    )


def _product_ref(product_name: str) -> str:
    """Use a short generic reference instead of the full product name."""
    if any(keyword in product_name for keyword in ("裤", "裙")):
        return "这条"
    if any(keyword in product_name for keyword in ("衬衫", "卫衣", "针织", "外套", "T恤", "羽绒")):
        return "这件"
    return "这款"


def _generate_ask_concern_message(
    product_name: str,
    color: str,
    behavior_context: Dict[str, Any],
    variant_idx: int,
    max_length: int,
) -> str:
    """Generate concern-discovery fallback messages."""
    product_ref = _product_ref(product_name)
    variants = [
        lambda: (
            f"我看你最近看了好几次{product_ref}，你现在更在意尺码版型还是搭配感呀？"
            if behavior_context.get("has_multiple_visits")
            else f"{product_ref}你现在主要是在看版型、颜色，还是想搭配日常场景呀？"
        ),
        lambda: (
            f"你刚刚在这边停留挺久的，是在纠结上身效果还是日常怎么搭配吗？"
            if behavior_context.get("has_long_stay")
            else f"{product_ref}你现在最想先确认的是版型、面料，还是搭配方向呀？"
        ),
        lambda: f"{product_ref}你更在意上身效果、面料手感，还是搭配场景呀？",
    ]
    return variants[variant_idx % len(variants)]()[:max_length]


def _generate_ask_size_message(
    product_name: str,
    color: str,
    behavior_context: Dict[str, Any],
    variant_idx: int,
    max_length: int,
) -> str:
    """Generate size/fit fallback messages."""
    product_ref = _product_ref(product_name)
    has_enter_buy_page = behavior_context.get("has_enter_buy_page", False)
    has_multiple_visits = behavior_context.get("has_multiple_visits", False)
    variants = [
        lambda: (
            f"我看你已经进到购买页了，你平时这类衣服更喜欢宽松一点还是合身一点？"
            if has_enter_buy_page
            else f"{product_ref}你平时这类衣服一般穿什么尺码？我可以帮你对一下。"
        ),
        lambda: (
            f"{product_ref}你现在是在纠结尺码，还是担心版型上身效果呀？"
            if has_multiple_visits
            else f"{product_ref}你平时这类单品偏爱修身一点还是宽松一点？"
        ),
        lambda: f"{product_ref}你平时这类款一般怎么选尺码？我可以帮你一起看下。",
    ]
    return variants[variant_idx % len(variants)]()[:max_length]


def _generate_reassure_comfort_message(
    product_name: str,
    color: str,
    tags: List[str],
    behavior_context: Dict[str, Any],
    variant_idx: int,
    max_length: int,
) -> str:
    """Generate fabric/feel reassurance fallback messages."""
    product_ref = _product_ref(product_name)
    feel_tags = [tag for tag in tags if tag in ["舒适", "轻便", "柔软", "透气", "百搭"]]
    feel_desc = feel_tags[0] if feel_tags else "穿着会比较舒服"
    has_multiple_visits = behavior_context.get("has_multiple_visits", False)
    variants = [
        lambda: f"{product_ref}{feel_desc}，你如果在意上身感受或者面料，我可以帮你细说下。",
        lambda: (
            f"{product_ref}{feel_desc}，你反复在看，是比较在意上身效果还是面料手感呀？"
            if has_multiple_visits
            else f"{product_ref}{feel_desc}，如果你担心上身感受，这块其实不用太担心。"
        ),
        lambda: f"{product_ref}面料和上身感受都比较友好，你如果在意这块我可以继续帮你看。",
    ]
    return variants[variant_idx % len(variants)]()[:max_length]


def _generate_scene_relate_message(
    product_name: str,
    color: str,
    scene: str,
    behavior_context: Dict[str, Any],
    variant_idx: int,
    max_length: int,
) -> str:
    """Generate scene/styling fallback messages."""
    product_ref = _product_ref(product_name)
    has_multiple_visits = behavior_context.get("has_multiple_visits", False)
    scene_text = scene or "日常"
    variants = [
        lambda: (
            f"{product_ref}挺适合{scene_text}穿的，你如果想走通勤或日常路线都比较好搭。"
            if scene
            else f"{product_ref}日常和通勤都比较好搭，你如果想看搭配方向我可以给你建议。"
        ),
        lambda: (
            f"{product_ref}放在{scene_text}场景里会比较顺，你现在是在想怎么搭更合适吗？"
            if has_multiple_visits
            else f"{product_ref}不管是{scene_text}还是日常穿都挺顺的。"
        ),
        lambda: f"{product_ref}做{scene_text}搭配会比较省心，你想我顺手给你搭配建议吗？",
    ]
    return variants[variant_idx % len(variants)]()[:max_length]


def _generate_soft_check_message(
    product_name: str,
    color: str,
    behavior_context: Dict[str, Any],
    variant_idx: int,
    max_length: int,
) -> str:
    """Generate soft check-in fallback messages for low intent."""
    product_ref = _product_ref(product_name)
    variants = [
        lambda: f"如果你后面还想看看{product_ref}的版型或搭配，我也可以帮你一起看。",
        lambda: f"{product_ref}你先慢慢看，有需要的话我再帮你补充尺码或搭配建议。",
        lambda: f"如果你后面想了解{product_ref}的面料、上身效果或搭配，我都可以帮你看。",
    ]
    return variants[variant_idx % len(variants)]()[:max_length]
