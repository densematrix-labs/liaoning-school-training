import csv
import io
from app.models.student import Class
from tests.test_acceptance_workflows import acceptance_data, domain_ids, _login


async def test_chinese_csv_contains_both_distributions_and_matches_scope(client, auth_headers, acceptance_data):
    path = '/api/v1/students/classes/' + acceptance_data['class'] + '/overview'
    data = (await client.get(path, headers=auth_headers)).json()
    r = await client.get(path + '.csv', headers=auth_headers)
    assert r.status_code == 200 and r.content.startswith(b'\xef\xbb\xbf')
    rows = list(csv.reader(io.StringIO(r.content.decode('utf-8-sig'))))
    start = rows.index(['成绩分布（按实训记录）'])
    assert rows[start + 1] == ['成绩区间', '实训记录数']
    assert rows[start + 2:start + 2 + len(data['score_distribution'])] == [[x['label'], str(x['count'])] for x in data['score_distribution']]
    start = rows.index(['能力值分段人数分布（按学生）'])
    for actual, expected in zip(rows[start + 2:], data['ability_score_bands']):
        assert actual == [expected['name'], *[str(b['count']) for b in expected['bands']], str(expected['missing_evidence_count']), str(data['student_count'])]
    assert ['毕业达标情况'] in rows and ['共性薄弱能力'] in rows
    for raw in ['label,count', 'score_distribution', 'average,threshold', 'ready_count']:
        assert raw not in r.text
    empty = await client.get(path + '.csv?date_from=2100-01-01', headers=auth_headers)
    assert empty.status_code == 200 and '2100-01-01' in empty.text
    assert '实训次数,0' in empty.text and '无该维度证据人数' in empty.text


async def test_csv_remains_authorized_and_formula_safe(client, test_db, acceptance_data):
    teacher = await _login(client, 'ACCEPT-T')
    student = await _login(client, 'ACCEPT-S')
    path = '/api/v1/students/classes/' + acceptance_data['class'] + '/overview.csv'
    assert (await client.get(path, headers=student)).status_code == 403
    async with test_db() as db:
        row = await db.get(Class, acceptance_data['class'])
        row.name = '=UNTRUSTED'
        await db.commit()
    r = await client.get(path, headers=teacher)
    assert r.status_code == 200 and "'=UNTRUSTED" in r.text
    async with test_db() as db:
        row = await db.get(Class, acceptance_data['class'])
        row.teacher_id = None
        await db.commit()
    assert (await client.get(path, headers=teacher)).status_code == 403
