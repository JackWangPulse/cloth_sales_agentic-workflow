"""Prompt builder for apparel copy generation with strict factual grounding."""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from app.models.product import Product
from app.schemas.copy_schemas import CopyStyle

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Builder for constructing prompts for apparel copy generation."""

    @staticmethod
    def build_copy_prompt(
        product: Product,
        style: CopyStyle,
        rag_context: Optional[List[str]] = None,
    ) -> str:
        """
        构建服饰文案生成提示词。

        核心原则：
        1. 当前商品信息是唯一事实来源
        2. RAG 内容仅用于表达方式参考或背景知识
        3. 禁止引入商品数据中不存在的新事实
        """
        logger.info(
            "[PROMPT] Building apparel prompt for product=%s style=%s",
            product.name,
            style.value,
        )

        product_name = product.name
        tags = product.tags or []
        tags_str = "、".join(tags) if tags else "百搭"
        attributes = product.attributes or {}
        color = attributes.get("color", "")
        scene = attributes.get("scene", "")
        material = attributes.get("material", "")
        season = attributes.get("season", "")
        price = product.price
        sku = product.sku

        style_descriptions = {
            CopyStyle.natural: "自然、亲切、像导购私聊推荐，强调上身效果和日常搭配感",
            CopyStyle.professional: "专业、克制、可信，强调面料、版型、场景和品质感",
            CopyStyle.funny: "轻松、有记忆点，但不能浮夸，要符合服饰导购语境",
        }
        style_desc = style_descriptions.get(style, style_descriptions[CopyStyle.natural])

        prompt_parts: list[str] = []

        if rag_context:
            prompt_parts.append("## 参考信息（仅用于表达方式参考，禁止使用其中的事实信息）：")
            prompt_parts.append(
                "以下内容仅用于参考服饰描述方式、穿搭语言和表达风格，不能把其中的价格、SKU、材质、颜色、版型等具体事实直接写入当前商品文案。"
            )
            prompt_parts.append("")
            prompt_parts.append("**严格禁止事项：**")
            prompt_parts.append("1. 禁止使用参考信息中的价格、SKU、材质、颜色、尺码等具体事实")
            prompt_parts.append("2. 禁止把其他商品的卖点、风格或适穿场景混入当前商品")
            prompt_parts.append("3. 只能参考表达方式，不能复制具体描述")
            prompt_parts.append("")
            prompt_parts.append("参考信息：")
            prompt_parts.append("")

            for i, chunk in enumerate(rag_context[:3], 1):
                cleaned_chunk = chunk
                cleaned_chunk = re.sub(r"\[SKU:[^\]]+\]", "", cleaned_chunk)
                cleaned_chunk = re.sub(r"SKU:\s*[A-Z0-9]+", "", cleaned_chunk, flags=re.IGNORECASE)
                cleaned_chunk = re.sub(r"价格为?\s*\d+\.?\d*\s*元", "", cleaned_chunk)
                cleaned_chunk = re.sub(r"\d+\.?\d*\s*元", "", cleaned_chunk)
                cleaned_chunk = re.sub(r"型号[：:]\s*[A-Z0-9]+", "", cleaned_chunk, flags=re.IGNORECASE)
                cleaned_chunk = cleaned_chunk.strip()
                if cleaned_chunk:
                    prompt_parts.append(f"{i}. {cleaned_chunk}")

            prompt_parts.append("")
            prompt_parts.append("---")
            prompt_parts.append("")

        prompt_parts.append("## 商品信息（唯一事实来源）：")
        prompt_parts.append(f"商品名称：{product_name}")
        if sku:
            prompt_parts.append(f"商品SKU：{sku}")
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
        prompt_parts.append("以上商品信息是唯一事实来源，所有文案必须严格基于这些信息。")
        prompt_parts.append("")

        prompt_parts.append("## 任务要求：")
        prompt_parts.append("请为以上服饰商品写一条适合导购推荐或朋友圈展示的文案。")
        prompt_parts.append("")
        prompt_parts.append("要求：")
        prompt_parts.append(f"1. 风格：{style_desc}")
        prompt_parts.append("2. 长度：30-50字")
        prompt_parts.append("3. 突出服饰的版型、材质、颜色、季节或搭配场景中的核心卖点")
        prompt_parts.append("4. 语言自然，不要像硬广，不要堆砌形容词")
        prompt_parts.append("5. 允许提及穿搭感受、通勤感、氛围感，但必须基于已有事实")
        prompt_parts.append("")
        prompt_parts.append("**严格约束：**")
        prompt_parts.append("1. 文案中的所有事实信息必须来自上面的商品信息")
        prompt_parts.append("2. 如果参考信息中有相似表达，只能参考语气和结构，不能引用事实")
        prompt_parts.append("3. 禁止编造尺码、面料细节、设计点、洗护方式等未提供信息")
        prompt_parts.append("4. 禁止将其他品类或其他 SKU 的特征写到当前商品")
        prompt_parts.append("")
        prompt_parts.append("只输出文案内容，不要额外解释。")

        prompt = "\n".join(prompt_parts)

        logger.info(
            "[PROMPT] Apparel prompt built (%s chars, rag_chunks=%s)",
            len(prompt),
            len(rag_context) if rag_context else 0,
        )
        logger.debug("[PROMPT] Prompt preview: %s...", prompt[:200])
        return prompt

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for a text."""
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        other_chars = len(text) - chinese_chars
        tokens = int(chinese_chars / 1.5 + other_chars / 4)
        return max(tokens, 1)
