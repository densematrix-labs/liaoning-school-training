# 实训室图片资源

## 目录结构

```
labs/
├── standard/           # 标准整洁的实训室图片（用于参考）
│   ├── room-001.jpg    # 机车模拟驾驶室
│   ├── room-002.jpg    # 电气系统实训台
│   └── room-003.jpg    # 机械维护实训区
└── messy/              # 杂乱的实训室图片（用于环境检查测试）
    ├── room-001-messy-1.jpg  # 有垃圾/工具乱放
    ├── room-001-messy-2.jpg  # 不同程度的杂乱
    └── ...
```

## 图片规格

- **分辨率**: 1920x1080 或 1280x720
- **格式**: JPEG (质量 85%)
- **命名规范**: `{room-id}-{type}.jpg`

## 标准图片要求（standard/）

每个实训室需要一张标准图片，展示：
- ✅ 设备摆放整齐
- ✅ 地面清洁无杂物
- ✅ 工具归位
- ✅ 安全标识清晰

## 测试图片要求（messy/）

每个实训室需要 2-3 张测试图片，包含不同程度的问题：

### 场景 1: 轻微问题（扣 10-20 分）
- 工具未归位
- 椅子位置不整齐

### 场景 2: 中度问题（扣 20-40 分）
- 地面有垃圾/碎屑
- 设备未关闭电源
- 物品堆放混乱

### 场景 3: 严重问题（扣 40-60 分）
- 明显安全隐患
- 油渍/液体泄漏
- 安全设备缺失

## 图片来源说明

### 生成方式
1. **AI 生成**: 使用 DALL-E 3 或 Midjourney 生成
2. **实拍**: 在真实实训室拍摄（需脱敏处理）
3. **Stock Photos**: 使用免版权图片并标注来源

### 当前状态
⚠️ **图片待生成** - DALL-E 配额暂时不可用

临时方案：使用占位图或通用工业实训室图片

## AI 生成 Prompt 参考

### 标准图片 Prompt
```
A clean and organized railway locomotive training workshop interior, 
HXD3C electric locomotive simulator station, professional industrial 
setting, control panels and monitors, safety equipment visible, 
Chinese vocational school environment, realistic photography style, 
bright lighting, 16:9 aspect ratio
```

### 杂乱图片 Prompt
```
A slightly messy railway workshop with tools scattered on workbench, 
some debris on floor, chairs not properly arranged, 
industrial training environment, realistic photography style
```
