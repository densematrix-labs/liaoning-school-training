"""One deterministic evaluator shared by current graphs and historical trends."""
from collections import defaultdict


def evaluate(scores, abilities, subs, decay=1.0):
    if not 0 < decay <= 1:
        raise ValueError("时间衰减系数必须在 0 到 1 之间")
    samples=defaultdict(list)
    scores=sorted(scores,key=lambda s:(s.calculated_at.isoformat() if s.calculated_at else "",s.id))
    for index,score in enumerate(scores):
        recency=decay**(len(scores)-index-1)
        for detail in (score.details or {}).values():
            maximum=float(detail.get("max_score",0))
            if maximum<=0:
                continue
            value=float(detail.get("score",0))/maximum
            for sub_id in detail.get("related_abilities",[]):
                samples[sub_id].append((value,maximum*recency))
    sub_values={key:sum(value*weight for value,weight in rows)/sum(weight for _,weight in rows) for key,rows in samples.items()}
    major_values={}
    for major in abilities:
        # Untested sub-abilities contribute zero, rather than inflating attainment.
        selected=[s for s in subs if s.major_ability_id==major.id and s.weight>0]
        weight=sum(s.weight for s in selected)
        major_values[major.id]=sum(sub_values.get(s.id,0)*s.weight for s in selected)/weight if weight else 0
    return {"sub":sub_values,"major":major_values,"ready":bool(abilities) and all(major_values.get(a.id,0)>=a.graduation_threshold for a in abilities)}


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
