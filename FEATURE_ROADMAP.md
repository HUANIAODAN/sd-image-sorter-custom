# 功能路线图 - SD Image Sorter

## 📋 功能完成度对照表

| 功能模块 | 状态 | 完成度 | 说明 |
|---------|------|--------|------|
| **Gallery 画廊** | ✅ 完整 | 100% | 扫描、识别、筛选、排序全部实现 |
| **AI Tagging 打标** | ⚠️ 部分 | 70% | WD14 基础支持，需添加更多模型 |
| **Sorting 排序** | ✅ 完整 | 100% | 自动分离和手动分拣都已实现 |
| **Censor Edit 打码编辑** | ❌ 缺失 | 0% | 需要全新实现 |
| **Similar Images 相似图** | ⚠️ 部分 | 50% | dhash 已实现，需升级为 CLIP |
| **Prompt Lab 提示词工坊** | ✅ 完整 | 100% | 标签反推和生成已实现 |
| **Artist Identification** | ❌ 缺失 | 0% | 需要全新实现 |
| **Image Reader** | ✅ 完整 | 100% | 参数读取已实现 |
| **Image Obfuscate** | ❌ 缺失 | 0% | 需要全新实现 |
| **Aesthetic Score** | ❌ 缺失 | 0% | 需要全新实现 |

## 🎯 实施优先级

### 第一阶段：核心功能增强

#### 1. CLIP-based 相似图搜索 ⭐⭐⭐
- 使用 CLIP embedding 进行语义相似度搜索
- 支持跨风格、跨角色的相似图查找
- 提供相似度评分

#### 2. Aesthetic Score 美学评分 ⭐⭐⭐
- 本地美学评分模型
- 自动评估图片质量
- 支持按美学分数筛选和排序

### 第二阶段：专业工具

#### 3. Censor Edit 打码编辑 ⭐⭐
- YOLO 自动检测敏感区域
- 打码方式：马赛克、高斯模糊、黑条、白条
- 画笔工具：画笔、铅笔、橡皮、仿制图章
- 队列式批量处理

#### 4. Artist Identification 画师识别 ⭐⭐
- 识别图片风格和可能的画师
- 支持常见画师数据库
- 提供置信度评分

### 第三阶段：辅助功能

#### 5. Image Obfuscate 加扰/解扰 ⭐
- 图片可逆加扰（带密码）
- 适合私密分享

#### 6. 更多 WD14 模型支持 ⭐
- EVA02、SwinV2、ConvNeXt、ViT 等

## 📦 新增依赖

```txt
transformers>=4.30.0
torch>=2.0.0
ultralytics>=8.0.0
opencv-python>=4.8.0
timm>=0.9.0
cryptography>=41.0.0
faiss-cpu>=1.7.4
```

## 🗂️ 数据库更新

```sql
ALTER TABLE images ADD COLUMN clip_embedding BLOB;
ALTER TABLE images ADD COLUMN aesthetic_score REAL;
ALTER TABLE images ADD COLUMN artist_name TEXT;
ALTER TABLE images ADD COLUMN artist_confidence REAL;
ALTER TABLE images ADD COLUMN is_censored BOOLEAN DEFAULT 0;
```

## 📊 预计工作量

- CLIP 相似搜索: 5天
- Aesthetic Score: 3.5天
- Censor Edit: 11天
- Artist ID: 5天
- Image Obfuscate: 5天
- WD14 扩展: 4天

**总计**: 约 33.5天
