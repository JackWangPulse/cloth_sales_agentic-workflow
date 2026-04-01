"""Prompt templates for apparel private-chat sales copy generation."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.models.product import Product

logger = logging.getLogger(__name__)

# Intent levels
INTENT_HIGH = "high"
INTENT_MEDIUM = "medium"
INTENT_LOW = "low"
INTENT_HESITATING = "hesitating"

FORBIDDEN_MARKETING_WORDS = [
    "太香了",
    "必入",
    "闭眼冲",
    "爆款",
    "秒杀",
    "抢购",
    "限时",
    "仅此一次",
    "错过后悔",
    "史上最值",
    "血赚",
    "亏本",
    "清仓",
    "最后机会",
]


def build_system_prompt() -> str:
    """构建服饰导购私聊场景的系统提示词。"""
    return """你是一位真实门店的服饰导购，正在通过微信与顾客进行 1 对 1 私聊。

## 角色要求：
1. **语气自然亲切**：像真实导购在聊天，不要像广告推销
2. **真实可信**：基于商品事实，不夸大不编造
3. **适度引导**：轻量建议，不强推不施压
4. **服饰语境**：优先从版型、材质、颜色、季节、搭配和场景来介绍商品

## 严格禁止：
1. **禁止使用营销词汇**：如"太香了"、"必入"、"闭眼冲"、"爆款"、"秒杀"等
2. **禁止夸大宣传**：不编造商品没有的特点
3. **禁止强推**：不要使用"必须"、"一定要"等强制语气
4. **禁止编造事实**：所有信息必须来自提供的商品数据

## 输出要求：
1. 长度：≤ 45 个中文字符（可配置）
2. 语气：自然、亲切、日常
3. 必须包含：一个轻量行动建议（尺码/场景/搭配/库存/活动/面料感受等）
4. 格式：纯文本，不要表情符号，不要换行"""


def build_user_prompt(
    product: Product,
    intent_level: str,
    intent_reason: str,
    behavior_summary: Optional[Dict] = None,
    max_length: int = 45,
) -> str:
    """构建服饰私聊导购场景的用户提示词。"""
    product_name = product.name
    tags = product.tags or []
    tags_str = "、".join(tags) if tags else ""
    attributes = product.attributes or {}
    color = attributes.get("color", "")
    scene = attributes.get("scene", "")
    material = attributes.get("material", "")
    season = attributes.get("season", "")
    price = product.price

    strategy = _get_strategy_by_intent(intent_level)

    prompt_parts = []
    prompt_parts.append("## 商品信息（唯一事实来源）：")
    prompt_parts.append(f"商品名称：{product_name}")
    if tags:
        prompt_parts.append(f"商品标签：{tags_str}")
    if color:
        prompt_parts.append(f"颜色：{color}")
    if scene:
        prompt_parts.append(f"适用场景：{scene}")
    if season:
        prompt_parts.append(f"适穿季节：{season}")
    if material:
        prompt_parts.append(f"材质：{material}")
    if price:
        prompt_parts.append(f"价格：{price}元")
    prompt_parts.append("")
    prompt_parts.append("**重要：所有话术内容必须基于以上商品信息，禁止编造任何信息。**")
    prompt_parts.append("")

    prompt_parts.append("## 顾客意图分析：")
    prompt_parts.append(f"意图级别：{intent_level}")
    prompt_parts.append(f"判断原因：{intent_reason}")
    if behavior_summary:
        visit_count = behavior_summary.get("visit_count", 0)
        avg_stay = behavior_summary.get("avg_stay_seconds", 0)
        has_favorite = behavior_summary.get("has_favorite", False)
        has_enter_buy_page = behavior_summary.get("has_enter_buy_page", False)

        behavior_info = []
        if visit_count > 0:
            behavior_info.append(f"访问 {visit_count} 次")
        if avg_stay > 0:
            behavior_info.append(f"平均停留 {avg_stay:.0f} 秒")
        if has_favorite:
            behavior_info.append("已收藏")
        if has_enter_buy_page:
            behavior_info.append("进入购买页")

        if behavior_info:
            prompt_parts.append(f"行为摘要：{'，'.join(behavior_info)}")
    prompt_parts.append("")

    prompt_parts.append("## 话术策略：")
    prompt_parts.append(strategy)
    prompt_parts.append("")

    prompt_parts.append("## 输出要求：")
    prompt_parts.append(f"1. 长度：≤ {max_length} 个中文字符")
    prompt_parts.append("2. 语气：自然、亲切、像导购私聊")
    prompt_parts.append("3. 必须包含：一个轻量行动建议（基于服饰场景）")
    if intent_level == INTENT_LOW:
        prompt_parts.append("4. 语气要克制，不要强推")
    else:
        prompt_parts.append("4. 适度引导，不强推不施压")
    prompt_parts.append("")
    prompt_parts.append("只输出话术内容，不要其他说明。")

    return "\n".join(prompt_parts)


def _get_strategy_by_intent(intent_level: str) -> str:
    """根据意图级别返回服饰导购策略建议。"""
    strategies = {
        INTENT_HIGH: """顾客购买意图强烈，可以主动推进：
- 建议询问尺码或版型偏好（“您平时喜欢修身一点还是宽松一点？”）
- 提醒库存或颜色选择
- 如有活动可轻量提及
- 强调上身效果、搭配感或通勤实穿性""",
        INTENT_HESITATING: """顾客处于犹豫状态，需要消除顾虑：
- 轻量提问，看顾客更在意版型、颜色还是搭配
- 强调通勤、日常、约会等适穿场景
- 说明材质手感或搭配友好度
- 避免强推，以询问和陪伴式推荐为主""",
        INTENT_MEDIUM: """顾客有一定兴趣，可以做场景化推荐：
- 结合场景推荐，如通勤、休闲、约会
- 结合颜色或版型做搭配建议
- 用轻松语气发起对话，鼓励继续了解""",
        INTENT_LOW: """顾客兴趣较低，保持克制：
- 轻量提醒商品特点即可
- 不要强推，不要连续催促
- 语气自然，给顾客保留空间""",
    }
    return strategies.get(intent_level, strategies[INTENT_MEDIUM])


def validate_copy_output(copy_text: str, max_length: int = 45) -> tuple[bool, Optional[str]]:
    """验证生成的服饰导购文案。"""
    if len(copy_text) > max_length:
        return False, f"文案长度 {len(copy_text)} 超过限制 {max_length}"

    for word in FORBIDDEN_MARKETING_WORDS:
        if word in copy_text:
            return False, f"文案包含禁止的营销词汇：{word}"

    if not copy_text or not copy_text.strip():
        return False, "文案为空"

    return True, None


def build_product_copy_system_prompt() -> str:
    """构建服饰商品话术生成的系统提示词。"""
    return """你是一位经验丰富的服饰导购，擅长用自然、亲切的语言介绍商品。

## 角色要求：
1. **真实可信**：基于商品事实，不夸大不编造
2. **自然亲切**：语气像真实导购推荐，不要像广告
3. **服饰导向**：优先突出版型、材质、颜色、搭配感、适穿场景

## 严格禁止：
1. **禁止使用营销词汇**：如"太香了"、"必入"、"闭眼冲"、"爆款"、"秒杀"等
2. **禁止夸大宣传**：不编造商品没有的特点
3. **禁止编造事实**：所有信息必须来自提供的商品数据
4. **禁止引用其他商品**：只介绍当前商品，不提及其他 SKU

## 输出要求：
1. 语气：自然、亲切、日常
2. 长度：符合指定要求（默认 ≤ 50 字符）
3. 内容：突出商品的实际价值和穿搭场景"""


def build_product_copy_user_prompt(
    product: Product,
    selling_points: List[str],
    scene: str = "guide_chat",
    style: str = "natural",
    max_length: int = 50,
) -> str:
    """构建服饰商品话术生成的用户提示词。"""
    product_name = product.name
    tags = product.tags or []
    attributes = product.attributes or {}
    color = attributes.get("color", "") if attributes else ""
    material = attributes.get("material", "") if attributes else ""
    scene_attr = attributes.get("scene", "") if attributes else ""
    season = attributes.get("season", "") if attributes else ""
    price = product.price

    scene_descriptions = {
        "guide_chat": "导购私聊场景（1 对 1 对话式开场，必须自然开启交流）",
        "moments": "朋友圈场景（适合分享，语气轻松）",
        "poster": "海报场景（简洁有力，突出服饰卖点）",
    }
    scene_desc = scene_descriptions.get(scene, scene_descriptions["guide_chat"])

    style_descriptions = {
        "natural": "自然、亲切、日常",
        "professional": "专业、可信、克制",
        "friendly": "友好、轻松、有距离感",
    }
    style_desc = style_descriptions.get(style, style_descriptions["natural"])

    prompt_parts = []
    prompt_parts.append("## 商品信息（唯一事实来源）：")
    prompt_parts.append(f"商品名称：{product_name}")
    if tags:
        prompt_parts.append(f"商品标签：{'、'.join(tags)}")
    if color:
        prompt_parts.append(f"颜色：{color}")
    if material:
        prompt_parts.append(f"材质：{material}")
    if season:
        prompt_parts.append(f"季节：{season}")
    if scene_attr:
        prompt_parts.append(f"适用场景：{scene_attr}")
    if price:
        prompt_parts.append(f"价格：{price}元")
    if selling_points:
        prompt_parts.append(f"核心卖点：{'；'.join(selling_points)}")
    prompt_parts.append("")
    prompt_parts.append("以上信息是唯一事实来源，不能编造未提供的信息。")
    prompt_parts.append("")

    prompt_parts.append("## 任务要求：")
    prompt_parts.append(f"请生成 2-3 条商品话术，用于{scene_desc}。")
    prompt_parts.append(f"风格要求：{style_desc}")
    prompt_parts.append(f"每条长度：≤ {max_length} 个中文字符")
    prompt_parts.append("")

    if scene == "guide_chat":
        prompt_parts.append("**重要：guide_chat 场景必须使用对话式骨架，像真实导购发出的第一句话。**")
        prompt_parts.append("")
        prompt_parts.append("强制要求：")
        prompt_parts.append("1. 开头尽量用“这件”“这款”“这条”这类自然指代，不要用完整商品名生硬开头")
        prompt_parts.append("2. 必须包含问句、邀请或轻量建议，像在开启对话")
        prompt_parts.append("3. 必须包含行动建议关键词之一：尺码 / 版型 / 搭配 / 场景 / 库存 / 活动 / 手感")
        prompt_parts.append("4. 禁止使用弱化短语：'可以看看' / '了解一下' / '值得入手'")
        prompt_parts.append("5. 禁止纯描述，不互动")
        prompt_parts.append("")
        prompt_parts.append("示例参考：")
        prompt_parts.append("这件黑色针织衫通勤穿会很显气质，您平时更喜欢修身一点还是宽松一点？")
        prompt_parts.append("这条牛仔裤版型挺利落的，日常搭卫衣也很好穿，您想看下深色还是浅色？")
    else:
        prompt_parts.append("输出为简洁完整的商品推荐句，突出核心卖点和穿搭场景。")
        prompt_parts.append("每条话术单独一行，用换行分隔，例如：")
        prompt_parts.append("这件白色衬衫利落又好搭，通勤和日常都很实穿")
        prompt_parts.append("黑色针织衫柔软亲肤，搭半裙或西装裤都很显气质")

    prompt_parts.append("")
    prompt_parts.append("只输出话术内容，不要其他说明：")
    return "\n".join(prompt_parts)
