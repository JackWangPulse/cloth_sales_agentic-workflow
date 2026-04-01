"""Message validators for safety and compliance checks (V5.6.0+)."""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Tuple

from app.services.prompt_templates import FORBIDDEN_MARKETING_WORDS

logger = logging.getLogger(__name__)

# guide_chat / primary 消息至少要带一个可执行建议信号。
ACTION_HINT_KEYWORDS = [
    "尺码",
    "码",
    "号",
    "版型",
    "上身",
    "面料",
    "材质",
    "搭配",
    "场景",
    "适合",
    "库存",
    "现货",
    "活动",
    "优惠",
    "风格",
    "颜色",
    "可以",
    "看看",
    "要不要",
    "方便",
]

# 对话里偏弱、偏空泛的表达，不适合作为主消息。
WEAK_PHRASES = [
    "可以看看",
    "真的不错",
    "挺适合你",
    "可以试试",
    "很好看",
    "挺不错的",
    "值得入手",
    "放心选择",
]

# Primary / guide_chat 的问题或邀请标记。
QUESTION_MARKERS = [
    "吗",
    "?",
    "？",
    "呢",
    "要不要",
    "方便",
    "喜欢",
    "需要",
    "库存还有",
    "哪个颜色",
    "哪个尺码",
    "更偏好",
]

INVITATION_PHRASES = [
    "要不要",
    "可以看看",
    "方便的话",
    "我帮你",
    "要不我",
    "我给你",
    "发你",
    "看看这款",
]


def validate_message(
    message: str,
    current_sku: str,
    max_length: int = 45,
    require_action_hint: bool = True,
    is_primary: bool = False,
    product_name: Optional[str] = None,
    recommended_action: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """Validate a single generated message."""
    if len(message) > max_length:
        return False, f"消息长度 {len(message)} 超过限制 {max_length}"

    if not message or not message.strip():
        return False, "消息不能为空"

    for word in FORBIDDEN_MARKETING_WORDS:
        if word in message:
            return False, f"消息包含禁用营销词：{word}"

    is_valid_sku, sku_error = validate_no_cross_sku_leakage(message, current_sku)
    if not is_valid_sku:
        return False, sku_error

    if require_action_hint:
        has_hint = any(keyword in message for keyword in ACTION_HINT_KEYWORDS)
        if not has_hint:
            return False, "消息缺少行动建议关键词"

    if is_primary:
        has_question = any(marker in message for marker in QUESTION_MARKERS)
        if not has_question:
            return False, "Primary 消息需要包含问题或轻邀请"

        if product_name and message.strip().startswith(product_name):
            return False, "Primary 消息不能以完整商品名开头（应使用'这款'/'这件'/'这条'等）"

        for weak_phrase in WEAK_PHRASES:
            if weak_phrase in message:
                return False, f"Primary 消息包含过弱表达：{weak_phrase}"

        if recommended_action:
            action_aligned = _check_action_alignment(message, recommended_action)
            if not action_aligned:
                return False, f"Primary 消息未对齐 recommended_action={recommended_action}"

    return True, None


def validate_no_cross_sku_leakage(message: str, current_sku: str) -> Tuple[bool, Optional[str]]:
    """Ensure the message does not leak another SKU."""
    sku_pattern = re.compile(r"\[SKU:([^\]]+)\]|SKU:\s*([A-Z0-9]+)", re.IGNORECASE)

    matches = sku_pattern.findall(message)
    if not matches:
        return True, None

    for match in matches:
        found_sku = (match[0] or match[1]).upper()
        if found_sku != current_sku.upper():
            return False, f"消息包含其他 SKU：{found_sku}，当前应为 {current_sku}"

    return True, None


def validate_message_pack(
    message_pack: List[dict],
    current_sku: str,
    max_length: int = 45,
    min_count: int = 3,
) -> Tuple[bool, Optional[str]]:
    """Validate a suggestion/message pack."""
    if len(message_pack) < min_count:
        return False, f"消息包数量 {len(message_pack)} 少于最小要求 {min_count}"

    strategies = [msg.get("strategy", "") for msg in message_pack]
    unique_strategies = set(strategies)
    if len(unique_strategies) < min_count:
        return False, f"消息包策略不够多样：{strategies}"

    for i, msg in enumerate(message_pack):
        message = msg.get("message", "")
        is_valid, error = validate_message(
            message=message,
            current_sku=current_sku,
            max_length=max_length,
            require_action_hint=True,
        )
        if not is_valid:
            return False, f"消息包第 {i + 1} 条校验失败：{error}"

    if len(message_pack) > 1:
        primary_message = message_pack[0].get("message", "")
        for i, msg in enumerate(message_pack[1:], 1):
            alt_message = msg.get("message", "")
            if alt_message in primary_message and len(alt_message) < len(primary_message) * 0.8:
                return False, f"备选消息 {i + 1} 与主消息过于相似"

    return True, None


def check_action_hint_presence(message: str) -> bool:
    """Return whether the message contains action-hint keywords."""
    return any(keyword in message for keyword in ACTION_HINT_KEYWORDS)


def validate_guide_chat_message(
    message: str,
    current_sku: str,
    product_name: str,
    max_length: int = 50,
    min_length: int = 10,
) -> Tuple[bool, Optional[str]]:
    """Validate a guide-chat style message."""
    if len(message) < min_length:
        return False, f"消息长度 {len(message)} 少于最小要求 {min_length}"
    if len(message) > max_length:
        return False, f"消息长度 {len(message)} 超过限制 {max_length}"

    if not message or not message.strip():
        return False, "消息不能为空"

    for word in FORBIDDEN_MARKETING_WORDS:
        if word in message:
            return False, f"消息包含禁用营销词：{word}"

    is_valid_sku, sku_error = validate_no_cross_sku_leakage(message, current_sku)
    if not is_valid_sku:
        return False, sku_error

    if message.strip().startswith(product_name):
        return False, "guide_chat 消息不能以完整商品名开头（应使用'这款'/'这件'/'这条'等）"

    has_question = any(marker in message for marker in QUESTION_MARKERS)
    has_invitation = any(phrase in message for phrase in INVITATION_PHRASES)
    if not (has_question or has_invitation):
        return False, "guide_chat 消息需要包含问题或轻邀请（如'要不要'/'可以看看'/'方便的话'等）"

    has_hint = any(keyword in message for keyword in ACTION_HINT_KEYWORDS)
    if not has_hint:
        return False, "guide_chat 消息必须包含行动建议关键词（尺码/版型/搭配/场景/库存/优惠等）"

    for weak_phrase in WEAK_PHRASES:
        if weak_phrase in message:
            return False, f"guide_chat 消息包含过弱表达：{weak_phrase}"

    return True, None


def _check_action_alignment(message: str, recommended_action: str) -> bool:
    """Check whether the message aligns with the recommended action."""
    action_keywords_map = {
        "ask_size": ["尺码", "码", "号", "版型", "偏宽松", "偏修身"],
        "ask_concern_type": ["在意", "更看重", "担心", "纠结", "偏好"],
        "reassure_comfort": ["舒服", "上身", "面料", "材质", "手感", "不用担心"],
        "scene_relate": ["场景", "适合", "搭配", "通勤", "日常", "约会"],
        "mention_stock": ["库存", "现货", "颜色", "尺码还有", "还有货"],
        "mention_promo": ["活动", "优惠", "折扣", "满减"],
        "soft_check_in": ["方便", "看看", "要不要", "可以", "有需要"],
    }

    keywords = action_keywords_map.get(recommended_action, [])
    if not keywords:
        return True

    return any(keyword in message for keyword in keywords)


def validate_primary_message(
    message: str,
    current_sku: str,
    product_name: str,
    recommended_action: str,
    max_length: int = 45,
) -> Tuple[bool, Optional[str]]:
    """Validate the primary message."""
    return validate_message(
        message=message,
        current_sku=current_sku,
        max_length=max_length,
        require_action_hint=True,
        is_primary=True,
        product_name=product_name,
        recommended_action=recommended_action,
    )
