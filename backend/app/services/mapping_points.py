"""Per-association contribution points, independent of training step scores."""
import math


def contribution_points(value):
    if isinstance(value, bool):
        raise ValueError('贡献分值必须为大于零的有限数值')
    try:
        points = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError('贡献分值必须为大于零的有限数值') from exc
    if not math.isfinite(points) or points <= 0:
        raise ValueError('贡献分值必须为大于零的有限数值')
    return points


def validate_mapping_points(mapping, configured):
    if not isinstance(configured, dict):
        raise ValueError('映射贡献分值必须按步骤和子能力配置')
    normalized = {}
    for step_id, entries in configured.items():
        if step_id not in mapping or not isinstance(entries, dict):
            raise ValueError('贡献分值引用未关联的步骤或子能力')
        if set(entries) - set(mapping[step_id]):
            raise ValueError('贡献分值引用未关联的步骤或子能力')
        normalized[step_id] = {sub_id: contribution_points(value) for sub_id, value in entries.items()}
    return normalized


def step_mapping_points(rules, step_id, related, default_points):
    configured = (rules or {}).get('ability_mapping_points', {})
    if not isinstance(configured, dict) or not isinstance(configured.get(step_id, {}), dict):
        raise ValueError('映射贡献分值结构错误')
    entries = configured.get(step_id, {})
    return {sub_id: contribution_points(entries.get(sub_id, default_points)) for sub_id in dict.fromkeys(related)}
