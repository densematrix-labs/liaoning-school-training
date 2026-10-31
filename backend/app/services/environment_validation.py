import math
import re

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
    # The image-only workflow has no supplied standard clauses, measurements
    # or observation history. Never silently turn those inventions into scores.
    factual = [data['summary'], *[text for item in data['categories'].values() for text in item['issues']]]
    leftover = data.get('leftover_items', {})
    if isinstance(leftover, dict) and isinstance(leftover.get('issues'), list):
        factual.extend(x for x in leftover['issues'] if isinstance(x, str))
    text = '\n'.join(factual)
    if re.search(r'(?<![A-Za-z])(?:GB(?:/T)?|JGJ|ISO|IEC)\s*[-/A-Z]*\s*\d', text, re.I):
        raise ValueError('AI引用了图片输入未提供的标准编号或条款，需人工核查；未生成检查结果')
    if re.search(r'\d+(?:\.\d+)?\s*(?:厘米|毫米|米|cm\b|mm\b)|长期滞留|因长期|由于长期|长期未清', text, re.I):
        raise ValueError('AI推断了图片无法确认的尺寸、距离或持续时间，需人工核查；未生成检查结果')
    data["needs_review"]=review
    return data
