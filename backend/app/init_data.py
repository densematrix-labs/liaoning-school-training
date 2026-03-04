"""Initialize database with mock data"""
import json
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.student import Major, Class, Student
from app.models.ability import MajorAbility, SubAbility, AbilityProfile
from app.models.lab import Lab, LabStatus
from app.models.training import TrainingProject, TrainingRecord, Score
from app.services.auth import AuthService


async def init_mock_data():
    """Initialize database with mock data if empty"""
    async with AsyncSessionLocal() as db:
        # Check if data exists
        result = await db.execute(select(User))
        if result.scalar_one_or_none():
            return  # Already has data
        
        print("Initializing mock data...")
        
        # Load abilities from JSON
        abilities_path = Path(__file__).parent.parent.parent / "mock-data" / "abilities.json"
        if abilities_path.exists():
            with open(abilities_path, "r", encoding="utf-8") as f:
                abilities_data = json.load(f)
        else:
            abilities_data = {"major_abilities": [], "sub_abilities": []}
        
        # Create major abilities
        ability_id_map = {}
        for i, ma_data in enumerate(abilities_data.get("major_abilities", [])):
            ma = MajorAbility(
                id=ma_data.get("id", str(uuid.uuid4())),
                name=ma_data["name"],
                description=ma_data.get("description"),
                weight=ma_data.get("weight", 0.17),
                graduation_threshold=0.6,
                icon=ma_data.get("icon"),
                display_order=i,
            )
            ability_id_map[ma_data["id"]] = ma.id
            db.add(ma)
        
        await db.flush()
        
        # Create sub abilities
        sub_ability_id_map = {}
        for sa_data in abilities_data.get("sub_abilities", []):
            sa = SubAbility(
                id=sa_data.get("id", str(uuid.uuid4())),
                major_ability_id=ability_id_map.get(sa_data["major_ability_id"], sa_data["major_ability_id"]),
                name=sa_data["name"],
                description=sa_data.get("description"),
                weight=sa_data.get("weight", 0.25),
            )
            sub_ability_id_map[sa_data["id"]] = sa.id
            db.add(sa)
        
        await db.flush()
        
        # Create major
        major = Major(
            id=str(uuid.uuid4()),
            code="500113",
            name="铁道信号自动控制",
            description="培养铁路信号设备维护、故障处理等技术人才",
        )
        db.add(major)
        await db.flush()
        
        # Create teacher users
        teachers = []
        teacher_data = [
            ("teacher1", "张明", "铁信2301班"),
            ("teacher2", "李华", "铁信2302班"),
        ]
        
        for username, name, _ in teacher_data:
            teacher_user = User(
                id=str(uuid.uuid4()),
                username=username,
                password_hash=AuthService.get_password_hash("123456"),
                name=name,
                role=UserRole.TEACHER,
            )
            db.add(teacher_user)
            teachers.append(teacher_user)
        
        await db.flush()
        
        # Create admin
        admin_user = User(
            id=str(uuid.uuid4()),
            username="admin",
            password_hash=AuthService.get_password_hash("admin123"),
            name="系统管理员",
            role=UserRole.ADMIN,
        )
        db.add(admin_user)
        await db.flush()
        
        # Create classes
        classes = []
        for i, (_, _, class_name) in enumerate(teacher_data):
            cls = Class(
                id=str(uuid.uuid4()),
                name=class_name,
                major_id=major.id,
                teacher_id=teachers[i].id,
                year=2023,
            )
            db.add(cls)
            classes.append(cls)
        
        await db.flush()
        
        # Create labs
        labs_data = [
            ("信号基础实训室", "实训中心A座", 1, 40),
            ("联锁实训室", "实训中心A座", 2, 30),
            ("行车调度实训室", "实训中心B座", 1, 50),
            ("客运服务实训室", "实训中心B座", 2, 60),
            ("通信设备实训室", "实训中心C座", 1, 35),
        ]
        
        labs = []
        for name, building, floor, capacity in labs_data:
            lab = Lab(
                id=str(uuid.uuid4()),
                name=name,
                building=building,
                floor=floor,
                capacity=capacity,
                equipment=["实训设备1", "实训设备2", "实训设备3"],
                status=random.choice([LabStatus.AVAILABLE, LabStatus.IN_USE]),
                current_students=random.randint(0, capacity // 2),
            )
            db.add(lab)
            labs.append(lab)
        
        await db.flush()
        
        # Create training projects
        projects = []
        project_data = [
            "色灯信号机检修",
            "转辙机检修",
            "轨道电路测试",
            "联锁系统操作",
            "信号设备日常巡检",
        ]
        
        sub_ability_ids = list(sub_ability_id_map.values())
        
        for name in project_data:
            steps = []
            for j in range(7):
                step_abilities = random.sample(sub_ability_ids, min(2, len(sub_ability_ids)))
                steps.append({
                    "id": f"step_{j+1}",
                    "name": f"步骤{j+1}: {'安全准备' if j==0 else '操作步骤' + str(j)}",
                    "order": j + 1,
                    "score": 10 + j * 2,
                    "abilities": step_abilities,
                })
            
            project = TrainingProject(
                id=str(uuid.uuid4()),
                name=name,
                major_id=major.id,
                lab_id=random.choice(labs).id,
                duration=90,
                max_score=100,
                steps=steps,
            )
            db.add(project)
            projects.append(project)
        
        await db.flush()
        
        # Create students
        students = []
        names = ["张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十",
                 "郑十一", "王小红", "李小明", "张小华", "刘小强", "陈小芳", "杨小伟"]
        
        for i, name in enumerate(names):
            cls = classes[i % len(classes)]
            
            # Create user
            student_user = User(
                id=str(uuid.uuid4()),
                username=f"student{i+1}",
                password_hash=AuthService.get_password_hash("123456"),
                name=name,
                role=UserRole.STUDENT,
            )
            db.add(student_user)
            await db.flush()
            
            # Create student
            student = Student(
                id=str(uuid.uuid4()),
                user_id=student_user.id,
                student_no=f"20230100{i+1:02d}",
                name=name,
                major_id=major.id,
                class_id=cls.id,
                enrollment_year=2023,
            )
            db.add(student)
            students.append(student)
        
        await db.flush()
        
        # Create scores for each student
        for student in students:
            num_scores = random.randint(5, 12)
            
            for _ in range(num_scores):
                project = random.choice(projects)
                base_score = random.uniform(60, 95)
                
                # Generate step details
                details = {}
                total_score = 0
                failed_abilities = []
                
                for step in project.steps:
                    step_max = step.get("score", 10)
                    passed = random.random() > 0.2
                    
                    if passed:
                        step_score = step_max
                        deduction = 0
                        reason = None
                    else:
                        deduction = random.randint(1, step_max // 2)
                        step_score = step_max - deduction
                        reason = random.choice(["操作不规范", "漏检项目", "记录不完整", "时间超限"])
                        failed_abilities.extend(step.get("abilities", []))
                    
                    total_score += step_score
                    details[step["id"]] = {
                        "passed": passed,
                        "score": step_score,
                        "max_score": step_max,
                        "deduction": deduction if not passed else None,
                        "reason": reason,
                        "related_abilities": step.get("abilities", []),
                    }
                
                # Create training record
                record = TrainingRecord(
                    id=str(uuid.uuid4()),
                    external_id=f"EXT-{uuid.uuid4().hex[:8]}",
                    student_id=student.id,
                    project_id=project.id,
                    steps_data=details,
                    completed_at=datetime.utcnow() - timedelta(days=random.randint(0, 60)),
                )
                db.add(record)
                await db.flush()
                
                # Create score
                score = Score(
                    id=str(uuid.uuid4()),
                    student_id=student.id,
                    project_id=project.id,
                    record_id=record.id,
                    total_score=total_score,
                    max_score=project.max_score,
                    details=details,
                    failed_abilities=list(set(failed_abilities)),
                    calculated_at=record.completed_at,
                )
                db.add(score)
            
            await db.flush()
            
            # Create ability profile
            major_ability_scores = {}
            for ma_id in ability_id_map.values():
                major_ability_scores[ma_id] = random.uniform(0.5, 0.95)
            
            sub_ability_scores = {}
            for sa_id in sub_ability_id_map.values():
                sub_ability_scores[sa_id] = random.uniform(0.4, 0.95)
            
            graduation_ready = all(v >= 0.6 for v in major_ability_scores.values())
            
            profile = AbilityProfile(
                id=str(uuid.uuid4()),
                student_id=student.id,
                major_abilities=major_ability_scores,
                sub_abilities=sub_ability_scores,
                graduation_ready=graduation_ready,
            )
            db.add(profile)
        
        await db.commit()
        print("Mock data initialized successfully!")
        print("Demo accounts:")
        print("  - Student: student1 / 123456")
        print("  - Teacher: teacher1 / 123456")
        print("  - Admin: admin / admin123")
