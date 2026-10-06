from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


CATEGORY_RULES = {
    "科技互联网": ("科技", "互联网", "大模型", "人工智能", "开源", "手机", "芯片", "推理", "开发者"),
    "社会民生": ("社区", "居民", "公交", "交通", "医院", "教育", "住房", "民生"),
    "商业财经": ("公司", "财报", "业绩", "利润", "营收", "投资", "市场", "消费"),
    "公共政策": ("政策", "部门", "法规", "补贴", "条例", "公告", "政府", "政务"),
    "文娱体育": ("演出", "电影", "音乐", "文娱", "赛事", "体育", "赛程", "比赛"),
}
RISK_WORDS = ("传闻", "未证实", "谣言", "伤亡", "个人信息", "身份资料", "泄露", "事故")


def _instant(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def analyze_hotspot(hotspot: Dict[str, Any]) -> Dict[str, Any]:
    text = hotspot["title"] + "\n" + hotspot["content_excerpt"]
    scores = {category: [word for word in words if word in text]
              for category, words in CATEGORY_RULES.items()}
    ranked = sorted(scores.items(), key=lambda item: len(item[1]), reverse=True)
    category, hits = ranked[0] if ranked and ranked[0][1] else ("其他", [])
    second = len(ranked[1][1]) if len(ranked) > 1 else 0
    ambiguous = bool(hits) and second >= len(hits)
    risk_flags = [word for word in RISK_WORDS if word in text]
    missing: List[str] = []
    if not hotspot.get("source_platform"):
        missing.append("来源平台")
    if not hotspot.get("source_url"):
        missing.append("原文链接")
    if not hotspot.get("published_at"):
        missing.append("发布时间")
    published = _instant(hotspot.get("published_at"))
    collected = _instant(hotspot.get("collected_at")) or datetime.now(timezone.utc)
    age_hours = (collected - published).total_seconds() / 3600 if published else None
    if age_hours is not None and age_hours < 0:
        risk_flags.append("发布时间晚于采集时间")
    if age_hours is not None and age_hours > 72:
        risk_flags.append("信息超过72小时")
    if hotspot.get("engagement_count") is not None and hotspot["engagement_count"] < 0:
        risk_flags.append("互动量无效")
    if category == "其他":
        missing.append("可判定的主题线索")
    if ambiguous:
        missing.append("明确的主要议题")

    confidence = 0.56 + min(len(hits), 4) * 0.075
    if len(hits) >= 2 and hotspot.get("source_platform") and hotspot.get("source_url") and published:
        confidence += 0.08
    if ambiguous:
        confidence -= 0.15
    confidence -= min(len(missing), 3) * 0.055
    if risk_flags:
        confidence -= 0.1
    confidence = round(max(0.35, min(0.95, confidence)), 2)
    engagement = hotspot.get("engagement_count") or 0
    attention = "high" if risk_flags or engagement >= 10000 else "medium" if engagement >= 1000 else "low"
    can_auto = bool(category != "其他" and len(hits) >= 2 and not ambiguous
                    and confidence >= 0.8 and not missing and not risk_flags)
    if missing:
        action_type = "request_information"
        action = "补充核实：{0}；由人工复核后再决定是否跟踪。".format("、".join(missing))
    elif risk_flags:
        action_type = "human_review"
        action = "存在需人工核验的信号：{0}；核实原始来源后再处理。".format("、".join(risk_flags))
    else:
        action_type = "auto_categorize" if can_auto else "human_review"
        action = "可加入自动归类候选队列，公开发布仍需人工决定。" if can_auto else "建议人工复核类别和关注等级。"
    evidence = ["命中主题词：" + "、".join(hits)] if hits else ["未命中明确主题词"]
    if hotspot.get("source_platform"):
        evidence.append("记录来源平台：" + hotspot["source_platform"])
    if hotspot.get("published_at"):
        evidence.append("记录发布时间：" + str(hotspot["published_at"]))
    if ambiguous:
        evidence.append("多类主题词并列，主要议题不明确")
    verification = [
        {"name": "来源与时间完整性", "status": "passed" if not missing else "warning",
         "detail": "信息完整" if not missing else "待补充：" + "、".join(missing)},
        {"name": "风险与时效校验", "status": "blocked" if risk_flags else "passed",
         "detail": "未命中风险" if not risk_flags else "需核验：" + "、".join(risk_flags)},
        {"name": "主题分类规则", "status": "passed" if len(hits) >= 2 and not ambiguous else "warning",
         "detail": "主题证据明确" if len(hits) >= 2 and not ambiguous else "主题证据不足或存在交叉"},
    ]
    return {
        "provider": "rules", "model": "local-rules-v1", "category": category,
        "attention_level": attention, "summary": hotspot["content_excerpt"][:180],
        "confidence": confidence, "evidence": evidence, "keywords": hits[:10], "entities": [],
        "can_auto_handle": can_auto, "action_type": action_type,
        "action_suggestion": action, "missing_information": missing,
        "verification": verification, "risk_flags": risk_flags,
    }
