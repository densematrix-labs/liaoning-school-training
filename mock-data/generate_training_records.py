#!/usr/bin/env python3
"""
生成模拟实训记录数据
运行: python generate_training_records.py > training_records.json
"""

import json
import random
from datetime import datetime, timedelta
import uuid

# 加载基础数据
with open('users.json', 'r', encoding='utf-8') as f:
    users_data = json.load(f)

with open('training_rooms.json', 'r', encoding='utf-8') as f:
    training_data = json.load(f)

students = users_data['students']
projects = training_data['training_projects']

# 配置
START_DATE = datetime(2025, 9, 1)  # 学期开始
END_DATE = datetime(2026, 3, 3)    # 当前日期
MIN_RECORDS_PER_STUDENT = 3
MAX_RECORDS_PER_STUDENT = 12

def generate_step_results(steps, skill_level):
    """
    根据学生能力水平生成步骤结果
    skill_level: 0.5-1.0，越高通过率越高
    """
    results = []
    for step in steps:
        # 基础通过概率 = 技能水平 * (1 - 步骤权重/2)
        # 权重越高的步骤越难通过
        base_prob = skill_level * (1 - step['score_weight'] / 2)
        passed = random.random() < base_prob
        results.append({
            "step_id": step['id'],
            "passed": passed,
            "timestamp": None  # 会在后面设置
        })
    return results

def calculate_score(step_results, steps):
    """计算总分"""
    total_score = 0
    for result, step in zip(step_results, steps):
        if result['passed']:
            total_score += step['score_weight'] * 100
    return round(total_score, 1)

def generate_records():
    records = []
    
    for student in students:
        # 为每个学生生成随机的技能水平 (0.6-0.95)
        skill_level = random.uniform(0.6, 0.95)
        
        # 随机选择实训次数
        num_records = random.randint(MIN_RECORDS_PER_STUDENT, MAX_RECORDS_PER_STUDENT)
        
        # 生成实训记录
        for _ in range(num_records):
            # 随机选择项目
            project = random.choice(projects)
            
            # 随机选择日期
            days_range = (END_DATE - START_DATE).days
            random_days = random.randint(0, days_range)
            record_date = START_DATE + timedelta(days=random_days)
            
            # 随机选择时间 (8:00 - 17:00)
            hour = random.randint(8, 17)
            minute = random.randint(0, 59)
            record_datetime = record_date.replace(hour=hour, minute=minute)
            
            # 生成步骤结果
            step_results = generate_step_results(project['steps'], skill_level)
            
            # 设置步骤时间戳
            step_time = record_datetime
            for result in step_results:
                result['timestamp'] = step_time.isoformat()
                step_time += timedelta(minutes=random.randint(1, 5))
            
            # 计算总分
            total_score = calculate_score(step_results, project['steps'])
            
            # 环境检查结果 (80% 通过率)
            env_check = None
            if random.random() < 0.7:  # 70% 的记录有环境检查
                env_passed = random.random() < 0.85
                env_check = {
                    "id": str(uuid.uuid4()),
                    "passed": env_passed,
                    "overall_score": random.randint(70, 100) if env_passed else random.randint(40, 69),
                    "issues": [] if env_passed else random.sample([
                        "工具未归位",
                        "台面有杂物",
                        "垃圾未清理",
                        "设备未关闭",
                        "安全帽未放回架子"
                    ], k=random.randint(1, 3)),
                    "created_at": (step_time + timedelta(minutes=5)).isoformat()
                }
            
            # 创建记录
            record = {
                "id": str(uuid.uuid4()),
                "student_id": student['id'],
                "project_id": project['id'],
                "room_id": project['room_id'],
                "step_results": step_results,
                "total_score": total_score,
                "passed": total_score >= 60,
                "duration_minutes": sum(random.randint(1, 5) for _ in project['steps']),
                "env_check_result": env_check,
                "created_at": record_datetime.isoformat(),
                "updated_at": record_datetime.isoformat()
            }
            records.append(record)
    
    # 按时间排序
    records.sort(key=lambda x: x['created_at'])
    
    return records

def generate_ability_snapshots():
    """基于实训记录生成能力快照"""
    # 这里简化处理，实际应该根据实训记录计算
    snapshots = []
    
    with open('abilities.json', 'r', encoding='utf-8') as f:
        abilities_data = json.load(f)
    
    major_abilities = abilities_data['major_abilities']
    
    for student in students:
        for ma in major_abilities:
            # 随机生成能力分数 (50-95)
            base_score = random.uniform(50, 95)
            # 添加一些波动
            score = min(100, max(0, base_score + random.uniform(-10, 10)))
            
            snapshot = {
                "id": str(uuid.uuid4()),
                "student_id": student['id'],
                "major_ability_id": ma['id'],
                "score": round(score, 1),
                "training_count": random.randint(3, 15),
                "trend": random.choice(["up", "down", "stable"]),
                "updated_at": datetime.now().isoformat()
            }
            snapshots.append(snapshot)
    
    return snapshots

def main():
    records = generate_records()
    snapshots = generate_ability_snapshots()
    
    output = {
        "training_records": records,
        "ability_snapshots": snapshots,
        "generated_at": datetime.now().isoformat(),
        "total_records": len(records),
        "total_snapshots": len(snapshots)
    }
    
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
