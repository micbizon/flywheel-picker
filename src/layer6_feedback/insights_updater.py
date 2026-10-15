from shared.config_loader import load_system_insights, save_system_insights

_AGENTS = {"fundamental", "technical", "sentiment", "ownership"}


def update_system_insights(feedback_result: dict) -> None:
    insights = load_system_insights()
    accuracy = insights.setdefault("agent_accuracy", {})

    most_predictive = feedback_result.get("most_predictive_agent", "")
    misleading = feedback_result.get("misleading_agent", "")
    quality = feedback_result.get("decision_quality", "")
    pattern = feedback_result.get("recurring_pattern", "").strip()

    if most_predictive in _AGENTS:
        agent = accuracy.setdefault(most_predictive, {"predictions": 0, "accurate": 0})
        agent["predictions"] = agent.get("predictions", 0) + 1
        if quality == "GOOD":
            agent["accurate"] = agent.get("accurate", 0) + 1

    if misleading in _AGENTS and misleading != most_predictive:
        agent = accuracy.setdefault(misleading, {"predictions": 0, "accurate": 0})
        agent["predictions"] = agent.get("predictions", 0) + 1

    if pattern:
        patterns: list = insights.setdefault("assumption_patterns", [])
        pattern_lower = pattern.lower()
        already_exists = any(
            pattern_lower in existing.lower() or existing.lower() in pattern_lower for existing in patterns
        )
        if not already_exists:
            patterns.append(pattern)

    save_system_insights(insights)
