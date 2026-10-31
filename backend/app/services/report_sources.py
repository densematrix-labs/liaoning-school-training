"""Read-only comparison of frozen report inputs with the authorized source rows."""
from sqlalchemy import select
from app.models.report import DiagnosticReport
from app.models.student import Student, Class
from app.models.training import Score, TrainingRecord, TrainingProject
from app.models.lab import EnvironmentCheck
from app.models.workflow import EnvironmentReview
from app.services.production_data import setting
from app.services.ability import AbilityService
from app.services.presentation import report_reference, training_record_reference


def comparison(label, saved, current):
    missing = saved is None or saved == ''
    return {'field': label, 'report_input': saved, 'source': current,
            'status': '报告未留存，无法核对' if missing else
                      '源数据未采集，无法判断' if current is None else
                      '一致' if saved == current else '不一致，需复核'}


def require_complete_report_steps(scores):
    """Do not convert missing observations into zero or failure."""
    for row in scores:
        if not row.get('steps'):
            raise ValueError('步骤数据未采集，无法判断完成情况；未生成诊断报告')
        for step in row['steps']:
            missing = [name for key, name in [('step_name', '步骤名称'), ('passed', '步骤状态'),
                       ('score', '步骤得分'), ('max_score', '步骤满分')]
                       if step.get(key) is None or step.get(key) == '']
            if missing:
                raise ValueError('、'.join(missing) + '未采集，无法判断；未生成诊断报告')
            if not isinstance(step['passed'], bool):
                raise ValueError('步骤状态无效，无法判断；未生成诊断报告')


async def report_sources(db, report: DiagnosticReport):
    metadata = await setting(db, 'report_meta:' + report.id, {})
    snap = metadata.get('snapshot', {})
    student = await db.get(Student, report.student_id)
    cls = await db.get(Class, student.class_id) if student else None
    rows = [comparison('学生姓名', snap.get('student_name'), student.name if student else None),
            comparison('班级', snap.get('class_name'), cls.name if cls else None)]
    records = []
    ids = metadata.get('score_ids', [report.score_id] if report.score_id else [])
    for i, sid in enumerate(ids):
        score = await db.get(Score, sid)
        frozen = (metadata.get('input_scores', []) + [{}] * (i + 1))[i]
        if not score:
            rows.append(comparison('成绩记录 ' + sid, frozen.get('total_score'), None))
            continue
        record = await db.get(TrainingRecord, score.record_id) if score.record_id else None
        project = await db.get(TrainingProject, score.project_id)
        completed = record.completed_at if record else score.calculated_at
        records.append({'score_id': sid, 'record_id': score.record_id,
                        'record_reference': training_record_reference(completed, score.record_id or sid),
                        'completed_at': completed.isoformat() if completed else None})
        rows += [comparison('项目', frozen.get('project_name'), project.name if project else None),
                 comparison('实训时间 UTC', frozen.get('completed_at'), completed.isoformat() if completed else None),
                 comparison('总分', frozen.get('total_score'), score.total_score),
                 comparison('满分', frozen.get('max_score'), score.max_score)]
        details = list((score.details or {}).values())
        # These legacy report snapshots did not retain step IDs. Compare by
        # unique frozen name, never silently pair different steps by position.
        for step in frozen.get('steps', []):
            matches = [d for d in details if d.get('step_name') == step.get('step_name')]
            source = matches[0] if len(matches) == 1 else {}
            name = step.get('step_name') or '名称未留存'
            rows += [comparison(name + ' · 名称', step.get('step_name'), source.get('step_name')),
                     comparison(name + ' · 得分', step.get('score'), source.get('score')),
                     comparison(name + ' · 满分', step.get('max_score'), source.get('max_score')),
                     comparison(name + ' · 状态', step.get('passed'), source.get('passed')),
                     comparison(name + ' · 原因', step.get('reason'), source.get('reason'))]
    profile = await AbilityService(db).get_student_profile(report.student_id)
    current = {r.name: r for r in profile.radar_data} if profile else {}
    abilities = []
    for row in metadata.get('input_abilities', []):
        source = current.get(row.get('name'))
        abilities.append({'name': row.get('name'), 'value': row.get('score'), 'threshold': row.get('threshold'),
                          'source_value': source.score if source else None,
                          'source_threshold': source.threshold if source else None,
                          'status': '达标' if row.get('score') is not None and row.get('threshold') is not None and row['score'] >= row['threshold'] else '未达标' if row.get('score') is not None and row.get('threshold') is not None else '未采集，无法判断',
                          'comparison': '一致' if source and source.score == row.get('score') and source.threshold == row.get('threshold') else '无法核对或已变化，需复核'})
    envs = list((await db.execute(select(EnvironmentCheck).where(EnvironmentCheck.student_id == report.student_id,
                    EnvironmentCheck.score_id.in_(ids)).order_by(EnvironmentCheck.checked_at.desc()))).scalars()) if ids else []
    frozen_ids={row['check_id'] for row in metadata.get('input_environment',[]) if row.get('check_id')}
    if frozen_ids:
        envs=[row for row in envs if row.id in frozen_ids]
    environment = []
    for env in envs:
        review = (await db.execute(select(EnvironmentReview).where(EnvironmentReview.check_id == env.id))).scalar_one_or_none()
        status = review.status if review else '需人工复核'
        value = None if status == 'rejected' else sum(v.get('score', 0) for v in (review.reviewed_details or {}).values() if isinstance(v, dict)) if review else env.total_score
        environment.append({'id': env.id, 'score_id': env.score_id, 'checked_at': env.checked_at.isoformat() if env.checked_at else None,
                            'score': value, 'review_status': status, 'summary': (review.reviewed_summary or env.summary) if review else env.summary,
                            'image': env.uploaded_image_url, 'details': (review.reviewed_details or env.details) if review else env.details})
    frozen_env = metadata.get('input_environment', [])
    return {'report_id': report.id, 'report_reference': report_reference(report.generated_at, report.id),
            'student_id': report.student_id, 'student_name': snap.get('student_name'), 'generated_at': report.generated_at,
            'records': records, 'rows': rows, 'abilities': abilities, 'history_scope': profile.history_scope if profile else None,
            'input_environment': frozen_env, 'environment': environment,
            'environment_status': '无关联环境记录，无法判断是否达标' if not frozen_env else ('已关联报告生成时使用的环境检查记录' if frozen_ids else '历史快照未保存环境ID/时间，以下为同成绩关联源记录，需结合分数及复核状态核对'),
            'scope_note': '对照的是报告生成时结构化输入与当前源数据，不等同于AI正文全部事实已校验；历史输入不回写。能力输入为生成时全历史画像，不是本次成绩单独推算。未采集的步骤原因不能推定；AI可能原因不是已确认事实。'}
