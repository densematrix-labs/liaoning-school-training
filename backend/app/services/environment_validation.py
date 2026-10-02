import math

CATEGORIES={"equipment_placement":30,"surface_cleanliness":30,"safety_compliance":20,"environmental_hygiene":20}


def validate_result(data):
    if not isinstance(data,dict) or not isinstance(data.get("categories"),dict) or set(data["categories"])!=set(CATEGORIES):
        raise ValueError("图片检查分项不完整")
    total=0
    review=bool(data.get("unreadable",False))
    for key,maximum in CATEGORIES.items():
        item=data["categories"][key]
        if not isinstance(item,dict):
            raise ValueError("图片检查分项结构无效")
        score=item.get("score")
        confidence=item.get("confidence")
        if not isinstance(score,int) or isinstance(score,bool) or not 0<=score<=maximum or item.get("max_score")!=maximum:
            raise ValueError("图片检查分值无效")
        if not isinstance(confidence,(int,float)) or not math.isfinite(confidence) or not 0<=confidence<=1:
            raise ValueError("图片检查置信度无效")
        if not isinstance(item.get("issues"),list) or any(not isinstance(x,str) for x in item["issues"]):
            raise ValueError("图片检查问题说明无效")
        review=review or confidence<0.85
        total+=score
    if data.get("total_score")!=total or not isinstance(data.get("summary"),str) or not data["summary"].strip():
        raise ValueError("图片总分或总体结论与分项不一致")
    if not isinstance(data.get("suggestions"),list) or any(not isinstance(x,str) for x in data["suggestions"]):
        raise ValueError("缺少建议措施")
    data["needs_review"]=review
    return data
