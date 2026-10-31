from datetime import datetime
from app.config import settings
from app.models.student import Student, Class
from app.models.training import Score
from app.models.user import User, UserRole
from tests.test_acceptance_workflows import acceptance_data, domain_ids, _login


async def test_class_ability_bands_are_student_counts_at_boundaries_and_missing_evidence(client, auth_headers, test_db, acceptance_data, monkeypatch):
    monkeypatch.setattr(settings, 'RELEASE_MODE', True)
    ids = acceptance_data
    async with test_db() as db:
        original = await db.get(Score, ids['score'])
        original.calculated_at = datetime(2026, 9, 1)
        for i, value in enumerate([0, 20, 40, 60, 80, 100, None]):
            uid, sid = f'band-user-{i}', f'band-student-{i}'
            db.add(User(id=uid, username=uid, name=f'分段学生{i}', role=UserRole.STUDENT, password_hash='not-used-in-login'))
            db.add(Student(id=sid, user_id=uid, student_no=f'BAND{i}', name=f'分段学生{i}', major_id=ids['major'], class_id=ids['class'], enrollment_year=2026))
            if value is not None:
                db.add(Score(id=f'band-score-{i}', student_id=sid, project_id=ids['project'], total_score=value, max_score=100,
                             calculated_at=datetime(2026, 10, 10), details={'step-1': {'score': value, 'max_score': 100, 'related_abilities': [ids['sub']]}}))
        db.add(Class(id='other-band-class', name='未授权分段班', major_id=ids['major'], year=2026))
        await db.commit()
    teacher = await _login(client, 'ACCEPT-T')
    path = f"/api/v1/students/classes/{ids['class']}/overview"
    r = await client.get(path, headers=teacher)
    assert r.status_code == 200
    data = r.json(); band = next(x for x in data['ability_score_bands'] if x['id'] == ids['ability'])
    assert data['student_count'] == band['student_count'] == 8
    assert [x['count'] for x in band['bands']] == [1, 1, 2, 1, 2]
    assert band['missing_evidence_count'] == 1 and band['observed_count'] == 7
    assert sum(x['count'] for x in band['bands']) + band['missing_evidence_count'] == 8
    # The 50% fixture and 0/20/40 are below the 60% boundary; 60/80/100 pass.
    assert data['ability_distribution'][0]['ready_count'] == 3
    filtered = (await client.get(path, headers=teacher, params={'date_from': '2026-10-10T00:00:00', 'date_to': '2026-10-10T23:59:59'})).json()
    band = filtered['ability_score_bands'][0]
    assert [x['count'] for x in band['bands']] == [1, 1, 1, 1, 2]
    assert band['missing_evidence_count'] == 2
    assert (await client.get('/api/v1/students/classes/other-band-class/overview', headers=teacher)).status_code == 403
    student = await _login(client, 'ACCEPT-S')
    assert (await client.get(path, headers=student)).status_code == 403
    empty = (await client.get('/api/v1/students/classes/other-band-class/overview', headers=auth_headers)).json()
    assert all(sum(x['count'] for x in row['bands']) == row['missing_evidence_count'] == 0 for row in empty['ability_score_bands'])
