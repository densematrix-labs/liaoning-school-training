"""
辽轨智能实训能力评估平台 - API
直接从 JSON 文件加载 Mock 数据
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
import random
from datetime import datetime

app = FastAPI(
    title="辽轨智能实训能力评估平台",
    description="职业学校实训能力评估 Demo API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load mock data
MOCK_DATA_PATH = "/app/mock-data"

def load_json(filename):
    """Load JSON file from mock-data directory"""
    path = os.path.join(MOCK_DATA_PATH, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Load all data at startup
ABILITIES_DATA = load_json("abilities.json")
USERS_DATA = load_json("users.json")
TRAINING_ROOMS_DATA = load_json("training_rooms.json")
TRAINING_RECORDS_DATA = load_json("training_records.json")

# ==================== Health Check ====================
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "liaoning-training-api"}

# ==================== Auth ====================
class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/v1/auth/login")
async def login(req: LoginRequest):
    """Login with student/teacher ID"""
    # Check students
    for student in USERS_DATA.get("students", []):
        if student["student_id"] == req.username and req.password == "123456":
            return {
                "access_token": f"demo_token_{req.username}",
                "token_type": "bearer",
                "user": {
                    "id": student["id"],
                    "username": req.username,
                    "name": student["name"],
                    "role": "student",
                    "class_id": student.get("class_id"),
                }
            }
    
    # Check teachers
    for teacher in USERS_DATA.get("teachers", []):
        if teacher["employee_id"] == req.username and req.password == "123456":
            return {
                "access_token": f"demo_token_{req.username}",
                "token_type": "bearer",
                "user": {
                    "id": teacher["id"],
                    "username": req.username,
                    "name": teacher["name"],
                    "role": "admin" if teacher.get("is_admin") else "teacher",
                }
            }
    
    raise HTTPException(status_code=401, detail="用户名或密码错误")

@app.get("/api/v1/auth/me")
async def get_me():
    return {
        "id": "demo",
        "username": "demo_user",
        "name": "演示用户",
        "role": "student"
    }

# ==================== Students ====================
@app.get("/api/v1/students")
async def get_students():
    """Get all students with class info"""
    students = USERS_DATA.get("students", [])
    classes = {c["id"]: c for c in USERS_DATA.get("classes", [])}
    
    result = []
    for stu in students:
        cls = classes.get(stu.get("class_id"), {})
        result.append({
            "id": stu["id"],
            "student_no": stu["student_id"],
            "name": stu["name"],
            "gender": stu.get("gender", "男"),
            "class_id": stu.get("class_id"),
            "class_name": cls.get("name", ""),
            "major": cls.get("major", "铁道机车运用与维护"),
            "enrollment_year": int(stu["student_id"][:4]),
        })
    
    return {"students": result, "total": len(result)}

@app.get("/api/v1/students/{student_id}")
async def get_student(student_id: str):
    """Get student detail"""
    for stu in USERS_DATA.get("students", []):
        if stu["id"] == student_id or stu["student_id"] == student_id:
            classes = {c["id"]: c for c in USERS_DATA.get("classes", [])}
            cls = classes.get(stu.get("class_id"), {})
            
            # Generate ability profile
            ability_profile = {}
            for ma in ABILITIES_DATA.get("major_abilities", []):
                ability_profile[ma["name"]] = round(random.uniform(0.55, 0.95), 2)
            
            return {
                "id": stu["id"],
                "student_no": stu["student_id"],
                "name": stu["name"],
                "gender": stu.get("gender", "男"),
                "class_name": cls.get("name", ""),
                "major": cls.get("major", "铁道机车运用与维护"),
                "enrollment_year": int(stu["student_id"][:4]),
                "ability_profile": ability_profile,
                "graduation_ready": all(v >= 0.6 for v in ability_profile.values()),
            }
    
    raise HTTPException(status_code=404, detail="学生不存在")

# ==================== Classes ====================
@app.get("/api/v1/classes")
async def get_classes():
    """Get all classes"""
    classes = USERS_DATA.get("classes", [])
    teachers = {t["id"]: t for t in USERS_DATA.get("teachers", [])}
    students = USERS_DATA.get("students", [])
    
    result = []
    for cls in classes:
        teacher = teachers.get(cls.get("teacher_id"), {})
        student_count = len([s for s in students if s.get("class_id") == cls["id"]])
        
        result.append({
            "id": cls["id"],
            "name": cls["name"],
            "major": cls.get("major", "铁道机车运用与维护"),
            "year": cls.get("grade", 2023),
            "teacher_name": teacher.get("name"),
            "student_count": student_count,
        })
    
    return {"classes": result}

# ==================== Abilities ====================
@app.get("/api/v1/abilities")
async def get_abilities():
    """Get ability system"""
    return ABILITIES_DATA

@app.get("/api/v1/abilities/profile/{student_id}")
async def get_ability_profile(student_id: str):
    """Get student ability profile"""
    # Generate random but consistent profile
    random.seed(hash(student_id))
    
    major_abilities = {}
    sub_abilities = {}
    
    for ma in ABILITIES_DATA.get("major_abilities", []):
        score = round(random.uniform(0.55, 0.95), 2)
        major_abilities[ma["id"]] = {
            "name": ma["name"],
            "score": score,
            "threshold": 0.6,
        }
    
    for sa in ABILITIES_DATA.get("sub_abilities", []):
        sub_abilities[sa["id"]] = {
            "name": sa["name"],
            "score": round(random.uniform(0.45, 0.95), 2),
        }
    
    random.seed()  # Reset
    
    return {
        "student_id": student_id,
        "major_abilities": major_abilities,
        "sub_abilities": sub_abilities,
        "graduation_ready": all(
            v["score"] >= v["threshold"] for v in major_abilities.values()
        ),
    }

# ==================== Labs ====================
@app.get("/api/v1/labs")
async def get_labs():
    """Get all training labs"""
    rooms = TRAINING_ROOMS_DATA.get("training_rooms", [])
    
    result = []
    for room in rooms:
        result.append({
            "id": room["id"],
            "name": room["name"],
            "description": room.get("description", ""),
            "location": room.get("location", ""),
            "capacity": room.get("capacity", 30),
            "equipment": room.get("equipment", []),
            "status": random.choice(["available", "in_use"]),
            "current_students": random.randint(0, room.get("capacity", 30) // 2),
            "reference_image": room.get("standard_image"),
        })
    
    return {"labs": result}

# ==================== Training Projects ====================
@app.get("/api/v1/projects")
async def get_projects():
    """Get all training projects"""
    projects = TRAINING_ROOMS_DATA.get("training_projects", [])
    rooms = {r["id"]: r for r in TRAINING_ROOMS_DATA.get("training_rooms", [])}
    
    result = []
    for proj in projects:
        room = rooms.get(proj.get("room_id"), {})
        result.append({
            "id": proj["id"],
            "name": proj["name"],
            "description": proj.get("description", ""),
            "lab_name": room.get("name", ""),
            "duration": proj.get("duration_minutes", 60),
            "difficulty": proj.get("difficulty", "中级"),
            "step_count": len(proj.get("steps", [])),
        })
    
    return {"projects": result}

@app.get("/api/v1/projects/{project_id}")
async def get_project(project_id: str):
    """Get project detail with steps"""
    for proj in TRAINING_ROOMS_DATA.get("training_projects", []):
        if proj["id"] == project_id:
            return proj
    
    raise HTTPException(status_code=404, detail="项目不存在")

# ==================== Dashboard ====================
@app.get("/api/v1/dashboard")
async def get_dashboard():
    """Get dashboard data for big screen"""
    students = USERS_DATA.get("students", [])
    classes = USERS_DATA.get("classes", [])
    rooms = TRAINING_ROOMS_DATA.get("training_rooms", [])
    
    # Class rankings
    class_ranking = []
    for i, cls in enumerate(classes):
        class_ranking.append({
            "className": cls["name"],
            "averageScore": round(85 - i * 1.5 + random.uniform(-2, 2), 1),
            "trainingCount": random.randint(50, 150),
            "rank": i + 1,
        })
    
    # Lab status
    lab_status = []
    for room in rooms:
        lab_status.append({
            "labId": room["id"],
            "labName": room["name"],
            "status": random.choice(["available", "in_use", "available"]),
            "currentStudents": random.randint(0, room.get("capacity", 30) // 2),
        })
    
    # Ability distribution
    ability_dist = {}
    for ma in ABILITIES_DATA.get("major_abilities", []):
        ability_dist[ma["name"]] = round(random.uniform(0.70, 0.90), 2)
    
    return {
        "realtime": {
            "activeStudents": random.randint(100, 200),
            "todayTrainings": random.randint(50, 150),
            "averageScore": round(random.uniform(78, 88), 1),
            "passRate": round(random.uniform(0.85, 0.95), 2),
        },
        "classRanking": sorted(class_ranking, key=lambda x: x["averageScore"], reverse=True),
        "abilityDistribution": ability_dist,
        "labStatus": lab_status,
        "trend": [
            {"date": f"2024-0{i+1}", "trainingCount": random.randint(200, 500), "passRate": round(random.uniform(0.82, 0.92), 2)}
            for i in range(6)
        ],
    }

# ==================== Scores ====================
@app.get("/api/v1/scores")
async def get_scores(student_id: Optional[str] = None, project_id: Optional[str] = None):
    """Get training scores"""
    records = TRAINING_RECORDS_DATA if isinstance(TRAINING_RECORDS_DATA, list) else TRAINING_RECORDS_DATA.get("records", [])
    
    if student_id:
        records = [r for r in records if r.get("student_id") == student_id]
    if project_id:
        records = [r for r in records if r.get("project_id") == project_id]
    
    return {"scores": records[:50], "total": len(records)}

# ==================== Environment Check ====================
class EnvCheckRequest(BaseModel):
    lab_id: str
    image_base64: str

@app.post("/api/v1/environment/check")
async def check_environment(req: EnvCheckRequest):
    """Check environment cleanliness from image"""
    # Mock analysis result
    issues = random.sample([
        "检测到地面有纸屑",
        "工具箱未关闭",
        "椅子未归位",
        "桌面有杂物",
        "安全标识被遮挡",
        "灭火器位置不当",
    ], k=random.randint(0, 3))
    
    base_score = 100 - len(issues) * 15
    
    return {
        "total_score": max(60, base_score),
        "passed": len(issues) <= 1,
        "categories": {
            "cleanliness": {"score": random.randint(75, 100), "issues": issues[:2]},
            "organization": {"score": random.randint(70, 95), "issues": []},
            "safety": {"score": random.randint(80, 100), "issues": issues[2:3] if len(issues) > 2 else []},
        },
        "issues": issues,
        "summary": f"检测完成，发现 {len(issues)} 个问题。" if issues else "环境整洁，符合标准。",
    }

# ==================== Reports ====================
class ReportRequest(BaseModel):
    student_id: str
    report_type: str = "single"

@app.post("/api/v1/reports/generate")
async def generate_report(req: ReportRequest):
    """Generate diagnostic report for student"""
    # Find student
    student = None
    for stu in USERS_DATA.get("students", []):
        if stu["id"] == req.student_id or stu["student_id"] == req.student_id:
            student = stu
            break
    
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    
    # Generate mock report
    return {
        "report_id": f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "student_name": student["name"],
        "generated_at": datetime.now().isoformat(),
        "summary": f"{student['name']}同学整体表现良好，各项能力指标均达到毕业要求。",
        "strengths": [
            "安全操作意识强",
            "设备使用熟练",
            "能够独立完成基本检修任务",
        ],
        "improvements": [
            "故障诊断速度可进一步提升",
            "文档记录规范性有待加强",
        ],
        "recommendations": [
            "建议加强电气故障诊断实训",
            "建议参与更多团队协作项目",
        ],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
