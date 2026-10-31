"""One deterministic evaluator shared by current graphs and historical trends."""
from collections import defaultdict
from app.services.mapping_points import contribution_points


def summarize_sub_abilities(scores, decay=1.0, weight_by_maximum=True):
    if decay != 1.0:
        raise ValueError("不支持时间衰减")
    samples=defaultdict(list)
    scores=sorted(scores,key=lambda s:(s.calculated_at.isoformat() if s.calculated_at else "",s.id))
    for index,score in enumerate(scores):
        recency=1.0
        for step_id, detail in (score.details or {}).items():
            maximum=float(detail.get("max_score",0))
            if maximum<=0:
                continue
            value=float(detail.get("score",0))/maximum
            for sub_id in dict.fromkeys(detail.get("related_abilities",[])):
                points = contribution_points(detail.get('ability_mapping_points', {}).get(sub_id, maximum))
                samples[sub_id].append({'value': value, 'weight': points, 'contribution_points': points,
                    'score': float(detail.get('score', 0)), 'max_score': maximum, 'recency_factor': recency if weight_by_maximum else 1.0,
                    'score_id': score.id, 'step_id': str(step_id), 'project_id': getattr(score, 'project_id', '')})
    summaries = {}
    for key, rows in samples.items():
        numerator = sum(row['value'] * row['weight'] for row in rows)
        denominator = sum(row['weight'] for row in rows)
        summaries[key] = {'method': '按映射贡献分值汇总',
            'weighted_earned': numerator,
            'effective_weight': denominator, 'percentage': round(numerator / denominator * 100, 1),
            'step_count': len({(row['project_id'], row['step_id']) for row in rows}),
            'evidence_count': len(rows), 'record_count': len({row['score_id'] for row in rows}),
            'contributions': [{**row, 'weighted_earned': row['value'] * row['weight']} for row in rows]}
    return {key: item['weighted_earned'] / item['effective_weight'] for key, item in summaries.items()}, summaries


def summarize_major_abilities(sub_values, abilities, subs):
    major_values={}
    calculations = []
    for major in abilities:
        # Untested sub-abilities contribute zero, rather than inflating attainment.
        selected=[s for s in subs if s.major_ability_id==major.id and s.weight>0]
        weight=sum(s.weight for s in selected)
        major_values[major.id]=sum(sub_values.get(s.id,0)*s.weight for s in selected)/weight if weight else 0
        calculations.append({'id': major.id, 'name': getattr(major, 'name', major.id),
            'threshold': major.graduation_threshold * 100,
            'full_score': weight, 'percentage': round(major_values[major.id] * 100, 1),
            'children': [{'id': sub.id, 'name': getattr(sub, 'name', sub.id), 'full_score': sub.weight,'earned_score':sub_values.get(sub.id,0)*sub.weight,
                          'percentage': sub_values.get(sub.id, 0) * 100} for sub in selected]})
    return major_values, calculations


def evaluate(scores, abilities, subs, decay=1.0):
    sub_values, _ = summarize_sub_abilities(scores, decay)
    major_values, _ = summarize_major_abilities(sub_values, abilities, subs)
    return {"sub":sub_values,"major":major_values,"ready":bool(abilities) and bool(subs) and all(s.id in sub_values for s in subs if s.weight>0) and all(major_values.get(a.id,0)>=a.graduation_threshold for a in abilities)}


def select_repeated(rows):
    """Preserve originals; evaluation selection is per configured project."""
    grouped=defaultdict(list)
    for score,project in rows:
        grouped[project.id].append((score,project))
    result=[]
    for pairs in grouped.values():
        mode=(pairs[0][1].scoring_rules or {}).get("repeat_mode","all")
        if mode=="latest":
            pairs=[max(pairs,key=lambda x:(x[0].calculated_at.isoformat() if x[0].calculated_at else "",x[0].id))]
        elif mode=="highest":
            pairs=[max(pairs,key=lambda x:(x[0].total_score/x[0].max_score if x[0].max_score else 0,x[0].id))]
        result.extend(pairs)
    return result


async def active_schema(db):
    from sqlalchemy import select
    from app.models.ability import MajorAbility,SubAbility
    from app.services.production_data import enabled
    majors=list((await db.execute(select(MajorAbility).order_by(MajorAbility.display_order))).scalars())
    subs=list((await db.execute(select(SubAbility))).scalars())
    majors=[a for a in majors if await enabled(db,'abilities',a.id)]
    ids={a.id for a in majors}
    subs=[s for s in subs if s.major_ability_id in ids and await enabled(db,'sub-abilities',s.id)]
    return majors,subs
