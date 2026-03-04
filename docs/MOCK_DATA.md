# Mock 数据设计文档

**项目名称**: 辽轨智能实训能力评估平台  
**版本**: v1.0  
**创建日期**: 2026-03-04

---

## 一、学校基本信息

### 1.1 学校概况

```yaml
school:
  name: 辽宁铁道职业技术学院
  short_name: 辽铁院
  code: LNTDXY
  location: 辽宁省锦州市
  type: 公办高等职业院校
  established: 1948
  motto: "厚德载物，自强不息"
  
  statistics:
    total_students: 8500
    total_teachers: 420
    majors_count: 28
    labs_count: 45
```

---

## 二、专业设置

### 2.1 铁路运输专业群

```yaml
major_groups:
  - id: railway_transport
    name: 铁路运输专业群
    
    majors:
      - id: railway_transportation
        name: 铁道交通运营管理
        code: 500112
        students_count: 320
        enrollment_year: [2023, 2024, 2025]
        description: 培养铁路行车组织、客运组织、货运组织等岗位技术人才
        
      - id: railway_signal
        name: 铁道信号自动控制
        code: 500113
        students_count: 280
        enrollment_year: [2023, 2024, 2025]
        description: 培养铁路信号设备维护、故障处理等技术人才
        
      - id: railway_communication
        name: 铁道通信与信息化技术
        code: 500114
        students_count: 240
        enrollment_year: [2023, 2024, 2025]
        description: 培养铁路通信设备运维、网络管理等技术人才
        
      - id: urban_rail_operation
        name: 城市轨道交通运营管理
        code: 500606
        students_count: 350
        enrollment_year: [2023, 2024, 2025]
        description: 培养城市轨道交通行车调度、客运服务等岗位人才
```

### 2.2 机电工程专业群

```yaml
  - id: mechatronics
    name: 机电工程专业群
    
    majors:
      - id: railway_vehicle
        name: 铁道车辆技术
        code: 500105
        students_count: 260
        enrollment_year: [2023, 2024, 2025]
        description: 培养铁道车辆检修、维护等技术人才
        
      - id: railway_engineering
        name: 铁道工程技术
        code: 500101
        students_count: 220
        enrollment_year: [2023, 2024, 2025]
        description: 培养铁路线路维护、工程施工等技术人才
```

---

## 三、能力体系设计

### 3.1 铁道交通运营管理专业能力体系

```yaml
ability_schema:
  major_id: railway_transportation
  major_name: 铁道交通运营管理
  
  major_abilities:
    - id: safety
      name: 安全操作能力
      weight: 0.25
      description: 掌握铁路运输安全规章，具备安全意识和应急处理能力
      graduation_threshold: 0.6
      
      sub_abilities:
        - id: safety_awareness
          name: 安全意识
          description: 理解安全生产方针政策，严格遵守安全操作规程
          
        - id: emergency_response
          name: 应急处理
          description: 能够识别常见事故隐患，掌握应急预案和处置流程
          
        - id: protective_equipment
          name: 防护装备使用
          description: 正确使用个人防护装备和安全设施
          
    - id: equipment
      name: 设备使用能力
      weight: 0.25
      description: 熟练操作铁路运输相关设备和系统
      graduation_threshold: 0.6
      
      sub_abilities:
        - id: signal_operation
          name: 信号设备操作
          description: 能够操作色灯信号机、转辙机等信号设备
          
        - id: communication_device
          name: 通信设备使用
          description: 熟练使用列车无线调度通信系统（GSM-R）
          
        - id: ticketing_system
          name: 票务系统操作
          description: 熟练操作客票发售与预订系统
          
    - id: procedure
      name: 规程执行能力
      weight: 0.25
      description: 严格执行铁路运输规章制度和作业标准
      graduation_threshold: 0.6
      
      sub_abilities:
        - id: standard_process
          name: 标准流程执行
          description: 按照《铁路技术管理规程》规范作业
          
        - id: documentation
          name: 行车日志填写
          description: 规范填写行车日志、交接班记录等文书
          
        - id: reporting
          name: 汇报沟通
          description: 按程序向上级汇报情况，与相邻岗位做好联控
          
    - id: professional
      name: 专业技术能力
      weight: 0.25
      description: 掌握铁路运输组织核心技能
      graduation_threshold: 0.6
      
      sub_abilities:
        - id: train_dispatch
          name: 列车调度
          description: 能够进行列车运行调整和调度指挥
          
        - id: shunting_operation
          name: 调车作业
          description: 掌握调车作业程序和安全规定
          
        - id: passenger_service
          name: 客运服务
          description: 具备旅客服务组织和应急疏散能力
```

### 3.2 铁道信号自动控制专业能力体系

```yaml
ability_schema:
  major_id: railway_signal
  major_name: 铁道信号自动控制
  
  major_abilities:
    - id: safety
      name: 安全操作能力
      weight: 0.25
      graduation_threshold: 0.6
      
      sub_abilities:
        - id: safety_awareness
          name: 安全意识
        - id: electrical_safety
          name: 电气安全
        - id: emergency_response
          name: 应急处理
          
    - id: equipment
      name: 设备维护能力
      weight: 0.25
      graduation_threshold: 0.6
      
      sub_abilities:
        - id: signal_maintenance
          name: 信号设备维护
        - id: interlock_system
          name: 联锁系统维护
        - id: block_system
          name: 闭塞系统维护
          
    - id: testing
      name: 检测调试能力
      weight: 0.25
      graduation_threshold: 0.6
      
      sub_abilities:
        - id: circuit_testing
          name: 电路检测
        - id: parameter_adjustment
          name: 参数调整
        - id: fault_diagnosis
          name: 故障诊断
          
    - id: technical
      name: 专业技术能力
      weight: 0.25
      graduation_threshold: 0.6
      
      sub_abilities:
        - id: circuit_reading
          name: 电路图识读
        - id: wiring_operation
          name: 配线施工
        - id: system_integration
          name: 系统集成
```

---

## 四、实训室设置

### 4.1 实训室列表

```yaml
labs:
  - id: lab_001
    name: 信号基础实训室
    building: 实训中心A座
    floor: 1
    capacity: 40
    equipment:
      - 色灯信号机模型 × 20
      - ZD6型电动转辙机 × 10
      - 轨道电路实训台 × 8
    majors: [railway_signal]
    reference_image: "/images/labs/signal_basic_standard.jpg"
    
  - id: lab_002
    name: 联锁实训室
    building: 实训中心A座
    floor: 2
    capacity: 30
    equipment:
      - 计算机联锁系统 × 6
      - 6502电气集中实训台 × 4
      - DS6-K5B型计轴设备 × 4
    majors: [railway_signal]
    reference_image: "/images/labs/interlock_standard.jpg"
    
  - id: lab_003
    name: 行车调度实训室
    building: 实训中心B座
    floor: 1
    capacity: 50
    equipment:
      - CTC调度集中系统 × 1
      - 模拟驾驶台 × 10
      - 行车指挥台 × 6
    majors: [railway_transportation, urban_rail_operation]
    reference_image: "/images/labs/dispatch_standard.jpg"
    
  - id: lab_004
    name: 客运服务实训室
    building: 实训中心B座
    floor: 2
    capacity: 60
    equipment:
      - 自动售检票机 × 8
      - 安检设备 × 2
      - 模拟候车厅 × 1
    majors: [railway_transportation, urban_rail_operation]
    reference_image: "/images/labs/passenger_standard.jpg"
    
  - id: lab_005
    name: 通信设备实训室
    building: 实训中心C座
    floor: 1
    capacity: 35
    equipment:
      - GSM-R基站模拟器 × 4
      - 光纤通信实训台 × 6
      - 数字程控交换机 × 2
    majors: [railway_communication]
    reference_image: "/images/labs/communication_standard.jpg"
```

---

## 五、实训项目设计

### 5.1 信号设备实训项目

```yaml
training_projects:
  - id: proj_001
    name: 色灯信号机检修
    major_id: railway_signal
    lab_id: lab_001
    duration: 90  # 分钟
    max_score: 100
    
    steps:
      - id: step_001
        name: 安全准备
        order: 1
        score: 10
        description: 穿戴防护用品，确认作业环境安全
        abilities: [safety_awareness, protective_equipment]
        criteria:
          pass: 正确穿戴安全帽、绝缘手套、绝缘鞋
          fail_cases:
            - 未穿戴安全帽: -5
            - 未穿戴绝缘手套: -3
            - 未穿戴绝缘鞋: -2
            
      - id: step_002
        name: 断电确认
        order: 2
        score: 15
        description: 确认信号机已断电，使用验电笔检测
        abilities: [electrical_safety, circuit_testing]
        criteria:
          pass: 使用验电笔确认无电后再作业
          fail_cases:
            - 未验电直接作业: -15
            - 验电方法错误: -8
            
      - id: step_003
        name: 灯泡检查
        order: 3
        score: 20
        description: 检查各灯位灯泡状态，更换损坏灯泡
        abilities: [signal_maintenance, fault_diagnosis]
        criteria:
          pass: 正确检查并更换损坏灯泡
          fail_cases:
            - 漏检灯泡: -10
            - 更换方法错误: -8
            - 未记录更换情况: -2
            
      - id: step_004
        name: 透镜清洁
        order: 4
        score: 15
        description: 清洁信号机透镜
        abilities: [signal_maintenance]
        criteria:
          pass: 使用专用清洁布清洁，无划痕
          fail_cases:
            - 使用不当工具: -8
            - 清洁不彻底: -5
            - 造成划痕: -10
            
      - id: step_005
        name: 电气检测
        order: 5
        score: 20
        description: 测量绝缘电阻、接地电阻
        abilities: [circuit_testing, parameter_adjustment]
        criteria:
          pass: 测量值符合标准（绝缘≥1MΩ，接地≤4Ω）
          fail_cases:
            - 测量方法错误: -10
            - 未记录测量值: -5
            - 数值超标未处理: -15
            
      - id: step_006
        name: 功能测试
        order: 6
        score: 10
        description: 通电测试各灯位显示
        abilities: [signal_maintenance, circuit_testing]
        criteria:
          pass: 各灯位显示正常，颜色纯正
          fail_cases:
            - 未逐一测试: -5
            - 有灯位不亮未处理: -10
            
      - id: step_007
        name: 记录填写
        order: 7
        score: 10
        description: 填写检修记录表
        abilities: [documentation]
        criteria:
          pass: 记录完整、清晰、规范
          fail_cases:
            - 记录不完整: -5
            - 数据错误: -8
            - 字迹潦草: -2
            
  - id: proj_002
    name: 转辙机检修
    major_id: railway_signal
    lab_id: lab_001
    duration: 120
    max_score: 100
    
    steps:
      - id: step_001
        name: 安全准备
        order: 1
        score: 10
        abilities: [safety_awareness, protective_equipment]
        
      - id: step_002
        name: 外观检查
        order: 2
        score: 15
        abilities: [signal_maintenance, fault_diagnosis]
        
      - id: step_003
        name: 机械部分检查
        order: 3
        score: 20
        abilities: [signal_maintenance]
        
      - id: step_004
        name: 电气部分检查
        order: 4
        score: 20
        abilities: [circuit_testing, electrical_safety]
        
      - id: step_005
        name: 动作测试
        order: 5
        score: 15
        abilities: [signal_maintenance, parameter_adjustment]
        
      - id: step_006
        name: 参数调整
        order: 6
        score: 10
        abilities: [parameter_adjustment]
        
      - id: step_007
        name: 记录填写
        order: 7
        score: 10
        abilities: [documentation]
```

### 5.2 行车调度实训项目

```yaml
  - id: proj_003
    name: 接发列车作业
    major_id: railway_transportation
    lab_id: lab_003
    duration: 60
    max_score: 100
    
    steps:
      - id: step_001
        name: 接收调度命令
        order: 1
        score: 15
        abilities: [reporting, standard_process]
        
      - id: step_002
        name: 确认进路空闲
        order: 2
        score: 20
        abilities: [train_dispatch, safety_awareness]
        
      - id: step_003
        name: 办理进路
        order: 3
        score: 20
        abilities: [signal_operation, standard_process]
        
      - id: step_004
        name: 开放信号
        order: 4
        score: 15
        abilities: [signal_operation]
        
      - id: step_005
        name: 监视列车进站
        order: 5
        score: 15
        abilities: [train_dispatch, safety_awareness]
        
      - id: step_006
        name: 填写行车日志
        order: 6
        score: 15
        abilities: [documentation]
```

---

## 六、学生数据

### 6.1 班级设置

```yaml
classes:
  - id: class_001
    name: 铁信2301班
    major_id: railway_signal
    year: 2023
    teacher_name: 张明
    students_count: 45
    
  - id: class_002
    name: 铁信2302班
    major_id: railway_signal
    year: 2023
    teacher_name: 李华
    students_count: 43
    
  - id: class_003
    name: 铁运2301班
    major_id: railway_transportation
    year: 2023
    teacher_name: 王强
    students_count: 48
    
  - id: class_004
    name: 城轨2301班
    major_id: urban_rail_operation
    year: 2023
    teacher_name: 赵丽
    students_count: 50
```

### 6.2 示例学生数据

```yaml
students:
  - id: stu_001
    student_no: "2023010001"
    name: 张三
    gender: male
    class_id: class_001
    major_id: railway_signal
    enrollment_year: 2023
    
  - id: stu_002
    student_no: "2023010002"
    name: 李四
    gender: male
    class_id: class_001
    major_id: railway_signal
    enrollment_year: 2023
    
  - id: stu_003
    student_no: "2023010003"
    name: 王小红
    gender: female
    class_id: class_001
    major_id: railway_signal
    enrollment_year: 2023
    
  # ... 更多学生
```

### 6.3 示例成绩数据

```yaml
scores:
  - id: score_001
    student_id: stu_001
    project_id: proj_001
    total_score: 85
    max_score: 100
    completed_at: "2026-02-20T14:30:00"
    details:
      step_001: { passed: true, score: 10 }
      step_002: { passed: true, score: 15 }
      step_003: { passed: true, score: 18, deduction: 2, reason: "未记录更换情况" }
      step_004: { passed: true, score: 15 }
      step_005: { passed: false, score: 10, deduction: 10, reason: "测量方法错误" }
      step_006: { passed: true, score: 10 }
      step_007: { passed: true, score: 7, deduction: 3, reason: "记录不完整" }
    failed_abilities: [circuit_testing, documentation]
    
  - id: score_002
    student_id: stu_001
    project_id: proj_002
    total_score: 92
    max_score: 100
    completed_at: "2026-02-25T10:00:00"
    details:
      step_001: { passed: true, score: 10 }
      step_002: { passed: true, score: 15 }
      step_003: { passed: true, score: 20 }
      step_004: { passed: true, score: 18, deduction: 2 }
      step_005: { passed: true, score: 15 }
      step_006: { passed: true, score: 8, deduction: 2 }
      step_007: { passed: true, score: 6, deduction: 4 }
    failed_abilities: []
```

### 6.4 示例能力图谱

```yaml
ability_profiles:
  - student_id: stu_001
    student_name: 张三
    major_id: railway_signal
    
    sub_abilities:
      safety_awareness: 0.85
      electrical_safety: 0.78
      emergency_response: 0.72
      signal_maintenance: 0.88
      interlock_system: 0.65
      block_system: 0.60
      circuit_testing: 0.70
      parameter_adjustment: 0.75
      fault_diagnosis: 0.82
      circuit_reading: 0.80
      wiring_operation: 0.68
      system_integration: 0.55
      
    major_abilities:
      safety: 0.78
      equipment: 0.71
      testing: 0.76
      technical: 0.68
      
    graduation_ready: true
    updated_at: "2026-03-01"
```

---

## 七、教师数据

```yaml
teachers:
  - id: teacher_001
    name: 张明
    employee_no: "T20150032"
    department: 铁道信号学院
    title: 副教授
    classes: [class_001]
    
  - id: teacher_002
    name: 李华
    employee_no: "T20180045"
    department: 铁道信号学院
    title: 讲师
    classes: [class_002]
    
  - id: teacher_003
    name: 王强
    employee_no: "T20120018"
    department: 铁道运输学院
    title: 教授
    classes: [class_003]
```

---

## 八、大屏展示数据

### 8.1 实时统计数据

```yaml
dashboard_data:
  realtime:
    activeStudents: 156
    todayTrainings: 89
    averageScore: 82.5
    passRate: 0.91
    
  classRanking:
    - className: 铁信2301班
      averageScore: 86.2
      trainingCount: 245
      rank: 1
    - className: 城轨2301班
      averageScore: 84.8
      trainingCount: 268
      rank: 2
    - className: 铁运2301班
      averageScore: 83.5
      trainingCount: 312
      rank: 3
    - className: 铁信2302班
      averageScore: 81.9
      trainingCount: 228
      rank: 4
      
  abilityDistribution:
    safety:
      avg: 0.82
      distribution: [5, 12, 25, 38, 20]  # 0-20, 20-40, 40-60, 60-80, 80-100
    equipment:
      avg: 0.75
      distribution: [8, 15, 28, 32, 17]
    testing:
      avg: 0.78
      distribution: [6, 14, 26, 35, 19]
    technical:
      avg: 0.71
      distribution: [10, 18, 30, 28, 14]
      
  trend:
    - date: "2026-02-01"
      trainingCount: 78
      averageScore: 79.5
      passRate: 0.85
    - date: "2026-02-02"
      trainingCount: 92
      averageScore: 81.2
      passRate: 0.88
    # ... 更多日期
    
  labStatus:
    - labId: lab_001
      labName: 信号基础实训室
      status: in_use
      currentStudents: 28
    - labId: lab_002
      labName: 联锁实训室
      status: available
      currentStudents: 0
    - labId: lab_003
      labName: 行车调度实训室
      status: in_use
      currentStudents: 35
```

---

*本文档提供 Demo 所需的完整 Mock 数据，实际部署时需替换为真实数据。*
