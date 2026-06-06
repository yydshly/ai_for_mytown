"""拍照诊断编排。

流程（一次 vision 调用，控成本 R-06）：
1. identify：vision provider 识别照片中最可能的病虫（或 mock / 未配置降级）
2. 对齐：把识别文本对齐到结构化知识条目（KnowledgeBase.find_mentions）
3. 用药护栏：每个命中病虫查农药表，未审核则导向农技员（ADR-010）
4. 组装：结构化结果 + 置信度提示 + 免责声明

设计为对 vision 是否可用都能优雅降级（R-07）。
"""
from __future__ import annotations

import logging
from typing import Any

from ...ai.base import Capability, ProviderConfigError
from ...ai.factory import make_provider
from .knowledge_base import KnowledgeBase, PestMatch

log = logging.getLogger("services.diagnose")

DISCLAIMER = (
    "本结果由 AI 结合公开农技资料生成，仅供参考。用药请以农药标签说明和当地"
    "农技部门指导为准；涉及重大决策请咨询专业农技员。"
)

VISION_PROMPT = (
    "你是陕西本地桃树农技顾问。请仔细看这张桃树照片（可能是叶、果、枝干），"
    "判断最可能的 1-2 种病虫害。\n"
    "只用中文，按以下格式简洁回答：\n"
    "最可能：<病虫名称>（可能性：高/中/低）\n"
    "依据：<你从照片看到的关键特征，一句话>\n"
    "备选：<另一个可能的病虫名称，或写'无'>\n"
    "如果照片太糊或信息不足以判断，请直接写：'照片信息不足'，并说明需要补拍哪个部位。\n"
    "已知本地常见：桃缩叶病、桃褐腐病、桃细菌性穿孔病、桃流胶病、桃蚜、桃小食心虫。"
    "请优先在这些里判断，但不要编造农药名。"
)

MOCK_IDENTIFICATION = (
    "最可能：桃褐腐病（可能性：中）\n"
    "依据：果面有灰褐色轮纹状霉层，近成熟期阴雨后多发。\n"
    "备选：无"
)


def _build_vision_provider(config: dict) -> Any | None:
    """从 config 懒构建 vision provider；缺 key/未启用则返回 None（不抛异常）。"""
    ai_cfg = config.get("ai") or {}
    name = ai_cfg.get("vision_provider") or ai_cfg.get("active")
    if not name:
        return None
    try:
        p = make_provider(name, ai_cfg)
    except ProviderConfigError as e:
        log.info("vision provider 未配置: %s", e)
        return None
    if not p.supports(Capability.VISION):
        log.info("provider %s 不支持 vision", name)
        return None
    return p


def _candidate_from_match(m: PestMatch, kb: KnowledgeBase) -> dict:
    pest = kb.pesticide_for(m.name)
    return {
        "name": m.name,
        "type": m.type,
        "symptoms": m.symptoms,
        "identify_cues": m.identify_cues,
        "confusable_with": m.confusable_with,
        "cultural_control": m.cultural_control,
        "source": m.source,
        "trust_level": m.trust_level,
        "review_status": m.review_status,
        "pesticide": {
            "status": pest.status,   # verified | pending | none
            "items": pest.items,
            "note": pest.note,
        },
    }


async def diagnose(
    *,
    kb: KnowledgeBase,
    config: dict,
    image_bytes: bytes,
    image_mime: str = "image/jpeg",
    user_note: str = "",
    force_mock: bool = False,
) -> dict:
    """执行一次拍照诊断，返回结构化结果。"""
    mode = "ai"
    identification = ""

    if force_mock:
        mode = "mock"
        identification = MOCK_IDENTIFICATION
    else:
        provider = _build_vision_provider(config)
        if provider is None:
            mode = "unconfigured"
        else:
            try:
                prompt = VISION_PROMPT
                if user_note:
                    prompt += f"\n用户补充：{user_note}"
                identification = await provider.vision(image_bytes, prompt, mime=image_mime)
            except Exception as e:  # 网络/接口错误 → 友好降级
                log.warning("vision 调用失败: %s", e)
                mode = "error"

    # 未配置/出错：返回可用的降级结果（不依赖 AI 也给农户价值）
    if mode in ("unconfigured", "error"):
        return {
            "mode": mode,
            "identification_raw": "",
            "candidates": [],
            "confidence_note": (
                "AI 识别暂不可用。" if mode == "unconfigured"
                else "网络或服务暂时不可用，请稍后再试。"
            ),
            "next_actions": ["稍后重试", "咨询农技员"],
            "disclaimer": DISCLAIMER,
        }

    # 对齐到结构化知识 + 用药护栏
    matches = kb.find_mentions(identification)
    candidates = [_candidate_from_match(m, kb) for m in matches]

    low_conf = ("可能性：低" in identification) or ("信息不足" in identification) or not candidates
    confidence_note = (
        "照片信息可能不足或把握不大，建议补拍清晰照片（叶正反面/果实特写/枝干），"
        "或咨询农技员确认。" if low_conf
        else "以下为初步判断，请结合实际症状核对；不确定时请咨询农技员。"
    )

    return {
        "mode": mode,
        "identification_raw": identification,
        "candidates": candidates,
        "confidence_note": confidence_note,
        "next_actions": (["补拍清晰照片", "咨询农技员"] if low_conf else ["核对症状", "咨询农技员"]),
        "disclaimer": DISCLAIMER,
    }
