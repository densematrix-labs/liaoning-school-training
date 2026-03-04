"""
Mock 数据加载服务
"""
import json
import logging
from pathlib import Path
from sqlalchemy import select
from passlib.context import CryptContext
import uuid

from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.student import Student, Class, Major
from app.models.training import TrainingProject, TrainingRecord, Score
from app.models.ability import MajorAbility, SubAbility, AbilityProfile
from app.models.lab import Lab

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Mock 数据目录
MOCK_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "mock-data"


async def load_mock_data():
    """加载所有 Mock 数据"""
    async with AsyncSessionLocal() as db:
        try:
            # 检查是否已有数据
            result = await db.execute(select(User).limit(1))
            if result.scalar_one_or_none():
                logger.info("数据库已有数据，跳过加载")
                return
            
            logger.info("开始加载 Mock 数据...")
            
            # 加载能力数据
            await load_abilities(db)
            
            # 加载用户数据
            await load_users(db)
            
            # 加载实训室和项目
            await load_training_rooms(db)
            
            # 加载实训记录
            await load_training_records(db)
            
            # 计算能力画像
            await calculate_ability_profiles(db)
            
            await db.commit()
            logger.info("Mock 数据加载完成")
            
        except Exception as e:
            logger.error(f"加载 Mock 数据失败: {e}")
            await db.rollback()
            raise


async def load_abilities(db):
    """加载能力数据"""
    abilities_file = MOCK_DATA_DIR / "abilities.json"
    if not abilities_file.exists():
        logger.warning("abilities.json 不存在")
        return
    
    with open(abilities_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 加载大类能力
    for i, ma in enumerate(data.get("major_abilities", [])):
        major_ability = MajorAbility(
            id=ma["id"],
            name=ma["name"],
            description=ma.get("description", ""),
            weight=ma.get("weight", 0.25),
            graduation_threshold=0.6,
            icon=ma.get("icon"),
            display_order=i
        )
        db.add(major_ability)
    
    # 加载子能力
    for sa in data.get("sub_abilities", []):
        sub_ability = SubAbility(
            id=sa["id"],
            major_ability_id=sa["major_ability_id"],
            name=sa["name"],
            description=sa.get("description", ""),
            weight=sa.get("weight", 0.25)
        )
        db.add(sub_ability)
    
    await db.flush()
    logger.info(f"加载了 {len(data.get('major_abilities', []))} 个大类能力")


async def load_users(db):
    """加载用户数据"""
    users_file = MOCK_DATA_DIR / "users.json"
    if not users_file.exists():
        logger.warning("users.json 不存在")
        return
    
    with open(users_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 创建专业
    major = Major(
        id="major-001",
        code="080501",
        name="铁道机车运用与维护",
        description="培养从事铁道机车运用、检修与维护的高技能人才"
    )
    db.add(major)
    
    # 创建班级和教师用户
    class_map = {}
    for cls_data in data.get("classes", []):
        # 创建教师用户
        teacher_id = cls_data.get("teacher_id")
        teacher_data = next(
            (t for t in data.get("teachers", []) if t["id"] == teacher_id),
            None
        )
        
        if teacher_data:
            # 检查是否已创建
            existing = await db.execute(
                select(User).where(User.username == teacher_data["employee_id"])
            )
            if not existing.scalar_one_or_none():
                teacher_user = User(
                    id=teacher_id,
                    username=teacher_data["employee_id"],
                    password_hash=pwd_context.hash("123456"),
                    name=teacher_data["name"],
                    role=UserRole.ADMIN if teacher_data.get("is_admin") else UserRole.TEACHER
                )
                db.add(teacher_user)
        
        # 创建班级
        cls = Class(
            id=cls_data["id"],
            name=cls_data["name"],
            major_id="major-001",
            teacher_id=teacher_id,
            year=cls_data.get("grade", 2023)
        )
        db.add(cls)
        class_map[cls_data["id"]] = cls
    
    await db.flush()
    
    # 创建学生用户
    for stu_data in data.get("students", []):
        # 创建用户
        user = User(
            id=f"user-{stu_data['id']}",
            username=stu_data["student_id"],
            password_hash=pwd_context.hash("123456"),
            name=stu_data["name"],
            role=UserRole.STUDENT
        )
        db.add(user)
        
        # 创建学生
        student = Student(
            id=stu_data["id"],
            user_id=f"user-{stu_data['id']}",
            student_no=stu_data["student_id"],
            name=stu_data["name"],
            major_id="major-001",
            class_id=stu_data["class_id"],
            enrollment_year=int(stu_data["student_id"][:4])
        )
        db.add(student)
    
    await db.flush()
    logger.info(f"加载了 {len(data.get('students', []))} 个学生")


async def load_training_rooms(db):
    """加载实训室数据"""
    rooms_file = MOCK_DATA_DIR / "training_rooms.json"
    if not rooms_file.exists():
        logger.warning("training_rooms.json 不存在")
        return
    
    with open(rooms_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 加载实训室
    for room in data.get("training_rooms", []):
        lab = Lab(
            id=room["id"],
            name=room["name"],
            building=room.get("location", "").split()[0] if room.get("location") else None,
            capacity=room.get("capacity", 10),
            equipment=room.get("equipment", []),
            reference_image_url=room.get("standard_image")
        )
        db.add(lab)
    
    # 加载实训项目
    for proj in data.get("training_projects", []):
        # 构建 ability_mapping
        ability_mapping = {}
        for step in proj.get("steps", []):
            ability_mapping[step["id"]] = step.get("ability_ids", [])
        
        project = TrainingProject(
            id=proj["id"],
            name=proj["name"],
            major_id="major-001",
            lab_id=proj.get("room_id"),
            duration=proj.get("duration_minutes", 45),
            max_score=100.0,
            steps=proj.get("steps", []),
            ability_mapping=ability_mapping
        )
        db.add(project)
    
    await db.flush()
    logger.info(f"加载了 {len(data.get('training_rooms', []))} 个实训室")


async def load_training_records(db):
    """加载实训记录"""
    records_file = MOCK_DATA_DIR / "training_records.json"
    if not records_file.exists():
        logger.warning("training_records.json 不存在")
        return
    
    with open(records_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    records = data.get("training_records", [])
    
    for rec in records:
        # 创建实训记录
        record = TrainingRecord(
            id=rec["id"],
            external_id=rec["id"],
            student_id=rec["student_id"],
            project_id=rec["project_id"],
            steps_data=rec.get("step_results", []),
            completed_at=rec.get("created_at")
        )
        db.add(record)
        
        # 创建成绩
        # 计算未通过的能力
        failed_abilities = []
        for step_result in rec.get("step_results", []):
            if not step_result.get("passed", True):
                # 从 step_id 推断能力 ID（简化处理）
                failed_abilities.append(step_result.get("step_id"))
        
        score = Score(
            id=str(uuid.uuid4()),
            student_id=rec["student_id"],
            project_id=rec["project_id"],
            record_id=rec["id"],
            total_score=rec.get("total_score", 0),
            max_score=100.0,
            details=rec.get("step_results", []),
            failed_abilities=failed_abilities
        )
        db.add(score)
    
    await db.flush()
    logger.info(f"加载了 {len(records)} 条实训记录")


async def calculate_ability_profiles(db):
    """计算学生能力画像"""
    # 获取所有学生
    students_result = await db.execute(select(Student))
    students = students_result.scalars().all()
    
    # 获取所有大类能力和子能力
    major_abilities_result = await db.execute(select(MajorAbility))
    major_abilities = {ma.id: ma for ma in major_abilities_result.scalars().all()}
    
    sub_abilities_result = await db.execute(select(SubAbility))
    sub_abilities = {sa.id: sa for sa in sub_abilities_result.scalars().all()}
    
    # 获取所有实训项目（用于能力映射）
    projects_result = await db.execute(select(TrainingProject))
    projects = {p.id: p for p in projects_result.scalars().all()}
    
    for student in students:
        # 获取学生的所有成绩
        scores_result = await db.execute(
            select(Score).where(Score.student_id == student.id)
        )
        scores = scores_result.scalars().all()
        
        if not scores:
            continue
        
        # 计算每个子能力的得分
        sub_ability_scores = {}
        sub_ability_counts = {}
        
        for score in scores:
            project = projects.get(score.project_id)
            if not project or not project.ability_mapping:
                continue
            
            # 分析每个步骤
            for step_data in score.details or []:
                step_id = step_data.get("step_id")
                passed = step_data.get("passed", False)
                
                # 获取该步骤关联的能力
                ability_ids = project.ability_mapping.get(step_id, [])
                
                for ability_id in ability_ids:
                    if ability_id not in sub_ability_scores:
                        sub_ability_scores[ability_id] = 0
                        sub_ability_counts[ability_id] = 0
                    
                    sub_ability_scores[ability_id] += 100 if passed else 0
                    sub_ability_counts[ability_id] += 1
        
        # 计算子能力平均分
        sub_abilities_avg = {}
        for ability_id, total in sub_ability_scores.items():
            count = sub_ability_counts.get(ability_id, 1)
            sub_abilities_avg[ability_id] = round(total / count, 1)
        
        # 计算大类能力得分
        major_abilities_scores = {}
        for ma_id, ma in major_abilities.items():
            # 找出该大类下的所有子能力
            related_subs = [
                sa for sa in sub_abilities.values()
                if sa.major_ability_id == ma_id
            ]
            
            if not related_subs:
                major_abilities_scores[ma_id] = 0
                continue
            
            # 计算加权平均
            total_score = 0
            total_weight = 0
            
            for sa in related_subs:
                if sa.id in sub_abilities_avg:
                    total_score += sub_abilities_avg[sa.id] * sa.weight
                    total_weight += sa.weight
            
            if total_weight > 0:
                major_abilities_scores[ma_id] = round(total_score / total_weight, 1)
            else:
                # 如果没有子能力数据，使用学生平均分
                avg_score = sum(s.total_score for s in scores) / len(scores)
                major_abilities_scores[ma_id] = round(avg_score, 1)
        
        # 判断是否达到毕业标准
        graduation_ready = all(
            score >= ma.graduation_threshold * 100
            for ma_id, score in major_abilities_scores.items()
            if (ma := major_abilities.get(ma_id))
        )
        
        # 创建能力画像
        profile = AbilityProfile(
            id=str(uuid.uuid4()),
            student_id=student.id,
            sub_abilities=sub_abilities_avg,
            major_abilities=major_abilities_scores,
            radar_data=[
                {"ability_id": ma_id, "score": score}
                for ma_id, score in major_abilities_scores.items()
            ],
            graduation_ready=graduation_ready
        )
        db.add(profile)
    
    await db.flush()
    logger.info(f"计算了 {len(students)} 个学生的能力画像")
