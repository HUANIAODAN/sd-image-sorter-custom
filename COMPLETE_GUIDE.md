# 🎊 SD Image Sorter - 完整更新指南

## 📅 更新日期：2026-06-06

---

## 🎯 本次更新总览

### 前端优化 ✅
- Visual Studio Code 浅色/深色主题
- 主题切换功能
- 优化的组件样式

### 新增功能 ✅
1. **美学评分** - AI 自动评估图片质量
2. **CLIP 相似搜索** - 智能语义搜索
3. **图片加扰/解扰** - 隐私保护加密

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd "D:\1.AI\3.SD 图片整理工具\sd-image-sorter-custom-2026-04-22-hotfix"
.\.venv\Scripts\activate
pip install transformers torch torchvision opencv-python cryptography
```

### 2. 数据库迁移

```bash
python migrate_add_new_features.py
```

### 3. 启动项目

```bash
.\run.ps1
```

### 4. 访问应用

打开浏览器：`http://localhost:8000`

---

## 📋 新功能 API

### 美学评分

```bash
# 评分单张图片
POST /api/aesthetic/score
{"image_id": 1}

# 批量评分
POST /api/aesthetic/batch
{"only_unscored": true}

# 统计信息
GET /api/aesthetic/stats
```

### CLIP 相似搜索

```bash
# 计算 embedding
POST /api/clip/compute-embedding
{"image_id": 1}

# 搜索相似图
GET /api/images/1/similar-clip?limit=24&threshold=0.7
```

### 图片加扰

```bash
# 加扰
POST /api/obfuscate/encrypt
form-data: file, password, method

# 解扰
POST /api/obfuscate/decrypt
form-data: file, password, method
```

---

## 🎨 VS Code 主题

- 点击右上角按钮切换主题
- 浅色：纯白背景 + VS 蓝
- 深色：经典 `#1e1e1e` 背景

---

## 📊 功能对照

| 功能 | 状态 |
|------|------|
| Gallery 画廊 | ✅ 完整 |
| AI Tagging | ✅ 完整 |
| Sorting | ✅ 完整 |
| Similar (dhash) | ✅ 完整 |
| **Similar (CLIP)** | ✅ **新增** |
| **Aesthetic Score** | ✅ **新增** |
| Prompt Lab | ✅ 完整 |
| Image Reader | ✅ 完整 |
| **Image Obfuscate** | ✅ **新增** |
| **VS Code Theme** | ✅ **新增** |
| Censor Edit | ❌ 待实施 |
| Artist ID | ❌ 待实施 |

---

## 🔧 故障排除

### 模型下载失败
- 检查网络连接
- 使用镜像：`export HF_ENDPOINT=https://hf-mirror.com`

### CUDA 内存不足
- 减小批量大小
- 使用 CPU 模式

### 依赖安装失败
- 确保 Python 3.8+
- 更新 pip：`pip install --upgrade pip`

---

## 📝 数据库更新

新增字段：
- `aesthetic_score` - 美学评分
- `clip_embedding` - CLIP 向量
- `artist_name` - 画师（预留）
- `is_censored` - 打码标记（预留）

---

## 🎯 未来计划

- 打码编辑器 (Censor Edit)
- 画师识别 (Artist ID)
- 扩展 WD14 模型
- FAISS 向量索引

---

## 🎉 总结

本次更新添加了：
- ✅ 美学评分
- ✅ CLIP 相似搜索
- ✅ 图片加扰
- ✅ VS Code 主题

SD Image Sorter 现已成为功能强大的图片管理工具！
