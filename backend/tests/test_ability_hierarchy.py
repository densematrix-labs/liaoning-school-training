from tests.test_acceptance_workflows import acceptance_data, domain_ids, _login
from app.config import settings


async def test_pass_score_is_independent_and_children_do_not_inherit(client, auth_headers, acceptance_data):
    ids=acceptance_data
    assert (await client.put(f"/api/v1/release/catalog/sub-abilities/{ids['sub']}",headers=auth_headers,json={'full_score':20})).status_code==200
    baseline=(await client.get(f"/api/v1/abilities/student/{ids['student']}",headers=auth_headers)).json()
    for threshold in [65,80]:
        changed=await client.put(f"/api/v1/release/catalog/abilities/{ids['ability']}",headers=auth_headers,json={'pass_score':threshold,'code':'A01'})
        assert changed.status_code==200
        tree=(await client.get('/api/v1/release/ability-hierarchy',headers=auth_headers)).json()
        parent=next(x for x in tree['items'] if x['id']==ids['ability']);child=parent['children'][0]
        assert parent['pass_score']==threshold and child['full_score']==20
        assert 'graduation_threshold' not in child and 'threshold_inherited_from' not in child
        profile=(await client.get(f"/api/v1/abilities/student/{ids['student']}",headers=auth_headers)).json()
        assert profile['sub_ability_details'][0]['score']==baseline['sub_ability_details'][0]['score']
        assert profile['total_score'] is None
    student=await _login(client,'ACCEPT-S')
    assert (await client.get('/api/v1/release/ability-hierarchy',headers=student)).status_code==403


async def test_hierarchy_preserves_disabled_configuration_but_excludes_from_current_evaluation(client, auth_headers, acceptance_data, monkeypatch):
    monkeypatch.setattr(settings, 'RELEASE_MODE', True)
    ids = acceptance_data
    assert (await client.put(f"/api/v1/release/catalog/sub-abilities/{ids['sub']}", headers=auth_headers,
                             json={'enabled': False})).status_code == 200
    tree = (await client.get('/api/v1/release/ability-hierarchy', headers=auth_headers)).json()
    parent = next(x for x in tree['items'] if x['id'] == ids['ability'])
    assert parent['children'][0]['enabled'] is False
    profile = (await client.get(f"/api/v1/abilities/student/{ids['student']}", headers=auth_headers)).json()
    assert profile['sub_ability_details'] == []
    assert (await client.put(f"/api/v1/release/catalog/abilities/{ids['ability']}", headers=auth_headers,
                             json={'enabled': False})).status_code == 200
    tree = (await client.get('/api/v1/release/ability-hierarchy', headers=auth_headers)).json()
    parent = next(x for x in tree['items'] if x['id'] == ids['ability'])
    assert not parent['enabled'] and not parent['children'][0]['effective_enabled']
    profile = (await client.get(f"/api/v1/abilities/student/{ids['student']}", headers=auth_headers)).json()
    assert profile['radar_data'] == []
