import base64
import copy
import pytest
from app.services.environment import EnvironmentCheckService
from app.config import settings
from tests.test_release_integrations import image_bytes


async def test_provider_receives_explicit_reference_and_site_roles_in_order(test_db, monkeypatch):
    monkeypatch.setattr(settings, 'RELEASE_MODE', True)
    reference = 'data:image/png;base64,' + base64.b64encode(image_bytes()).decode()
    site = reference
    captured = []
    async def fake(messages, **kwargs):
        assert messages[0]['role'] == 'system' and '不得估测' in messages[0]['content']
        captured.extend(next(m['content'] for m in messages if m['role'] == 'user'))
        return {'total_score':100,'summary':'仅用于传输角色校验','suggestions':['保持整理'], 'unreadable':False,
                'leftover_items':{'status':'none_visible','issues':['未见明显遗留物']},
                'categories':{k:{'score':maximum,'max_score':maximum,'issues':[], 'confidence':.9} for k,maximum in [('equipment_placement',30),('surface_cleanliness',30),('safety_compliance',20),('environmental_hygiene',20)]}}, 'test-model'
    monkeypatch.setattr('app.services.ai_gateway.completion', fake)
    async with test_db() as db:
        service = EnvironmentCheckService(db)
        service.reference_images = [reference]
        result = await service._call_vlm_check(site, reference, '演示室')
    assert result['total_score'] == 100
    image_indexes = [i for i, item in enumerate(captured) if item['type']=='image_url']
    assert len(image_indexes) == 2
    assert captured[image_indexes[0]-1]['text'].startswith('标准状态参考图片 1/1')
    assert captured[image_indexes[1]-1]['text'].startswith('以下为唯一待检查现场图片')
    assert captured[image_indexes[0]]['image_url']['url'] == reference
    assert captured[image_indexes[1]]['image_url']['url'] == site


@pytest.mark.parametrize('unsupported', ['违反GB/T 36107-2018第5.4条', '布料约30厘米', '距离讲台3米', '因长期滞留造成积灰'])
def test_unsupported_norms_measurements_and_duration_do_not_silently_score(unsupported):
    from app.services.environment_validation import validate_result
    data = {'total_score': 100, 'summary': '通道可见工具箱', 'suggestions': ['收回工具箱'],
            'categories': {k: {'score': maximum, 'max_score': maximum, 'issues': [], 'confidence': .9} for k, maximum in [('equipment_placement',30),('surface_cleanliness',30),('safety_compliance',20),('environmental_hygiene',20)]}}
    assert validate_result(copy.deepcopy(data))['total_score'] == 100
    data['categories']['equipment_placement']['issues'] = [unsupported]
    with pytest.raises(ValueError, match='未生成检查结果'):
        validate_result(data)
