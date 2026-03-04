"""Initialize database with mock data from JSON files"""
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


MOCK_DATA_DIR = Path(__file__).parent.parent.parent / "mock-data"


def load_json(filename):
    """Load JSON file from mock-data directory"""
    path = MOCK_DATA_DIR / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


async def init_mock_data():
    """Initialize database with mock data if empty"""
    async with AsyncSessionLocal() as db:
        # Check if data exists
        result = await db.execute(select(User))
        if result.scalar_one_or_none():
            return  # Already has data
        
        print("Initializing mock data from JSON files...")
        
        # Load all mock data
        abilities_data = load_json("abilities.json")
        users_data = load_json("users.json")
        training_rooms_data = load_json("training_rooms.json")
        
        # ==================== ABILITIES ====================
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
        print(f"✓ Created {len(ability_id_map)} major abilities, {len(sub_ability_id_map)} sub abilities")
        
        # ==================== MAJORS & CLASSES ====================
        # Create major for all classes
        major = Major(
            id=str(uuid.uuid4()),
            code="500113",
            name="铁道机车运用与维护",
            description="培养具备铁道机车操作、检修、维护能力的高素质技术技能人才",
        )
        db.add(major)
        await db.flush()
        
        # Create classes from mock data
        class_id_map = {}
        teacher_id_map = {}
        
        # First create teachers
        for teacher_data in users_data.get("teachers", []):
            teacher_user = User(
                id=teacher_data["id"],
                username=teacher_data["employee_id"],
                password_hash=AuthService.get_password_hash("123456"),
                name=teacher_data["name"],
                role=UserRole.ADMIN if teacher_data.get("is_admin") else UserRole.TEACHER,
            )
            db.add(teacher_user)
            teacher_id_map[teacher_data["id"]] = teacher_user.id
        
        await db.flush()
        print(f"✓ Created {len(teacher_id_map)} teachers")
        
        # Then create classes
        for cls_data in users_data.get("classes", []):
            cls = Class(
                id=cls_data["id"],
                name=cls_data["name"],
                major_id=major.id,
                teacher_id=teacher_id_map.get(cls_data.get("teacher_id")),
                year=cls_data.get("grade", 2023),
            )
            db.add(cls)
            class_id_map[cls_data["id"]] = cls.id
        
        await db.flush()
        print(f"✓ Created {len(class_id_map)} classes")
        
        # ==================== LABS ====================
        lab_id_map = {}
        for room_data in training_rooms_data.get("training_rooms", []):
            # Parse location
            location = room_data.get("location", "")
            building = "实训楼"
            floor = 1
            if "A 区" in location:
                building = "实训楼 A 区"
            elif "B 区" in location:
                building = "实训楼 B 区"
            if "101" in location or "102" in location:
                floor = 1
            elif "201" in location or "202" in location:
                floor = 2
            
            lab = Lab(
                id=room_data["id"],
                name=room_data["name"],
                building=building,
                floor=floor,
                capacity=room_data.get("capacity", 30),
                equipment=room_data.get("equipment", []),
                reference_image_url=room_data.get("standard_image"),
                status=random.choice([LabStatus.AVAILABLE, LabStatus.IN_USE]),
                current_students=random.randint(0, room_data.get("capacity", 30) // 3),
            )
            db.add(lab)
            lab_id_map[room_data["id"]] = lab.id
        
        await db.flush()
        print(f"✓ Created {len(lab_id_map)} labs")
        
        # ==================== TRAINING PROJECTS ====================
        project_id_map = {}
        for proj_data in training_rooms_data.get("training_projects", []):
            # Convert steps to database format
            steps = []
            for step in proj_data.get("steps", []):
                steps.append({
                    "id": step["id"],
                    "name": step["name"],
                    "order": step["sequence"],
                    "score": int(step.get("score_weight", 0.1) * 100),
                    "abilities": step.get("ability_ids", []),
                    "description": step.get("description", ""),
                })
            
            project = TrainingProject(
                id=proj_data["id"],
                name=proj_data["name"],
                major_id=major.id,
                lab_id=lab_id_map.get(proj_data.get("room_id")),
                duration=proj_data.get("duration_minutes", 60),
                max_score=100,
                steps=steps,
                difficulty=proj_data.get("difficulty", "中级"),
            )
            db.add(project)
            project_id_map[proj_data["id"]] = project
        
        await db.flush()
        print(f"✓ Created {len(project_id_map)} training projects")
        
        # ==================== STUDENTS ====================
        students = []
        for stu_data in users_data.get("students", []):
            # Create user account
            student_user = User(
                id=stu_data["id"],
                username=stu_data["student_id"],
                password_hash=AuthService.get_password_hash("123456"),
                name=stu_data["name"],
                role=UserRole.STUDENT,
            )
            db.add(student_user)
            await db.flush()
            
            # Create student record
            student = Student(
                id=str(uuid.uuid4()),
                user_id=student_user.id,
                student_no=stu_data["student_id"],
                name=stu_data["name"],
                major_id=major.id,
                class_id=class_id_map.get(stu_data.get("class_id")),
                enrollment_year=int(stu_data["student_id"][:4]),
            )
            db.add(student)
            students.append(student)
        
        await db.flush()
        print(f"✓ Created {len(students)} students")
        
        # ==================== TRAINING RECORDS & SCORES ====================
        projects = list(project_id_map.values())
        sub_ability_ids = list(sub_ability_id_map.values())
        
        total_records = 0
        for student in students:
            num_scores = random.randint(3, 8)
            
            for _ in range(num_scores):
                project = random.choice(projects)
                
                # Generate step details
                details = {}
                total_score = 0
                failed_abilities = []
                
                for step in project.steps:
                    step_max = step.get("score", 10)
                    passed = random.random() > 0.15
                    
                    if passed:
                        step_score = step_max
                        deduction = 0
                        reason = None
                    else:
                        deduction = random.randint(1, max(1, step_max // 2))
                        step_score = max(0, step_max - deduction)
                        reason = random.choice([
                            "操作不规范", 
                            "漏检项目", 
                            "记录不完整", 
                            "时间超限",
                            "未按规程操作",
                            "安全意识不足"
                        ])
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
                
                completed_at = datetime.utcnow() - timedelta(
                    days=random.randint(0, 90),
                    hours=random.randint(0, 12)
                )
                
                # Create training record
                record = TrainingRecord(
                    id=str(uuid.uuid4()),
                    external_id=f"REC-{uuid.uuid4().hex[:8].upper()}",
                    student_id=student.id,
                    project_id=project.id,
                    steps_data=details,
                    completed_at=completed_at,
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
                    calculated_at=completed_at,
                )
                db.add(score)
                total_records += 1
            
            await db.flush()
            
            # Create ability profile for this student
            major_ability_scores = {}
            for ma_id in ability_id_map.values():
                major_ability_scores[ma_id] = round(random.uniform(0.55, 0.95), 2)
            
            sub_ability_scores = {}
            for sa_id in sub_ability_id_map.values():
                sub_ability_scores[sa_id] = round(random.uniform(0.45, 0.95), 2)
            
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
        
        print(f"✓ Created {total_records} training records")
        print("\n" + "="*50)
        print("Mock data initialized successfully!")
        print("="*50)
        print("\n📋 Demo accounts (password: 123456):")
        print("  Students:")
        for stu in users_data.get("students", [])[:5]:
            print(f"    - {stu['student_id']} ({stu['name']})")
        if len(users_data.get("students", [])) > 5:
            print(f"    ... and {len(users_data.get('students', [])) - 5} more")
        print("  Teachers:")
        for teacher in users_data.get("teachers", []):
            role = "管理员" if teacher.get("is_admin") else "教师"
            print(f"    - {teacher['employee_id']} ({teacher['name']}, {role})")
        print("="*50)
