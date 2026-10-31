import csv
import io
from datetime import datetime

from app.models.student import Class
from app.models.training import Score
from tests.test_acceptance_workflows import acceptance_data, domain_ids, _login


async def test_teacher_list_export_includes_all_pages_and_preserves_filters(client, test_db, acceptance_data):
    ids = acceptance_data
    async with test_db() as db:
        db.add_all([Score(id=f'export-{i:03}', student_id=ids['student'], project_id=ids['project'],
                          total_score=i, max_score=300, details={}, failed_abilities=[],
                          calculated_at=datetime(2026, 10, 10)) for i in range(205)])
        db.add(Class(id='unassigned', name='未授权班级', major_id=ids['major'], year=2026))
        await db.commit()
    teacher = await _login(client, 'ACCEPT-T')
    path = f"/api/v1/scores/class/{ids['class']}/export.csv"
    params = {'student_id': ids['student'], 'project_id': ids['project'],
              'date_from': '2026-10-10T00:00:00', 'date_to': '2026-10-10T23:59:59'}
    result = await client.get(path, params=params, headers=teacher)
    assert result.status_code == 200
    rows = list(csv.DictReader(io.StringIO(result.content.decode('utf-8-sig'))))
    assert len(rows) == 205
    assert {r['成绩ID'] for r in rows} == {f'export-{i:03}' for i in range(205)}
    assert sum(float(r['成绩']) for r in rows) == sum(range(205))
    assert len(list(csv.DictReader(io.StringIO((await client.get(path, params={**params, 'project_id': 'other'}, headers=teacher)).content.decode('utf-8-sig'))))) == 0
    assert (await client.get('/api/v1/scores/class/unassigned/export.csv', headers=teacher)).status_code == 403
    student = await _login(client, 'ACCEPT-S')
    assert (await client.get(path, headers=student)).status_code == 403
    assert (await client.get(path)).status_code in (401, 403)
    assert (await client.get(f"/api/v1/scores/{ids['score']}/steps.csv", headers=teacher)).status_code == 200
