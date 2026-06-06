# SD Image Sorter Custom - 瀑布流增强版 🎨

<div align="center">

![Version](https://img.shields.io/badge/version-2.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

一个功能强大的本地 Stable Diffusion 图片管理工具，具有 **Pinterest 风格瀑布流布局**、智能标签、参数提取、相似图搜索等功能。

[English](#english) | [中文](#chinese)

![Screenshot](docs/screenshot.png)

</div>

---

## ✨ 核心特性

### 🖼️ **瀑布流画廊视图**
- **Pinterest 风格 5 列布局**：图片按原始比例展示，自动填充最短列
- **纯 JavaScript 实现**：无外部依赖，加载速度快
- **响应式设计**：窗口大小改变时自动重新布局
- **流畅动画**：平滑的过渡效果

### 🔍 **强大的筛选与排序**
- **多维度筛选**：
  - 生成器（ComfyUI / NovelAI / WebUI / Forge）
  - 内容分级（general / sensitive / questionable / explicit）
  - 标签、Checkpoint、LoRA、Prompt 关键词
  - 图片尺寸、长宽比、星级
- **智能排序**：最新、最旧、文件名、星级、Prompt 长度、标签数量等

### 📊 **元数据提取**
支持主流 AI 绘图工具的元数据提取：
- ComfyUI
- NovelAI
- WebUI / Automatic1111
- Forge

自动识别并提取：
- Prompt（正向和负向）
- Checkpoint / LoRA / VAE
- Steps、CFG Scale、Sampler
- Seed、分辨率等参数

### 🏷️ **自动标签系统**
- **WD14 模型支持**：基于深度学习的图像标签识别
- **批量处理**：后台任务队列，实时进度显示
- **智能回退**：无模型时自动使用文件名提取标签

### 🎨 **Prompt Lab**
- 从图库反推可复用 Prompt
- 质量预设（高/中/无）
- 自动生成负向 Prompt
- 随机标签补足功能

### 🔎 **相似图搜索**
- 基于感知哈希（pHash）的近似图检测
- 支持图库内搜索和外部图片上传搜索
- 相似度百分比显示

### ⌨️ **快捷键分拣模式**
- `W / A / S / D`：移动到 4 个预设目录
- `Space`：跳过当前图片
- `Z`：撤销上一步操作
- 实时预览和进度显示

### 📖 **Image Reader**
无需扫描入库，直接拖拽图片即可读取元数据

---

## 🚀 快速开始

### 系统要求

- Python 3.8+
- Windows / Linux / macOS
- 8GB+ RAM（推荐）

### 安装与启动

#### Windows

**方式 1：双击运行**
```
双击 run.bat
```

**方式 2：PowerShell**
```powershell
.\run.ps1
```

#### Linux / macOS

```bash
chmod +x run.sh
./run.sh
```

### 访问界面

启动成功后，打开浏览器访问：
- **前端界面**：http://localhost:8000
- **健康检查**：http://localhost:8000/api/health

---

## 📖 使用指南

### 1️⃣ 扫描图库

1. 在左侧 **扫描图库** 区域输入图片目录路径
2. 勾选"递归"可扫描子目录
3. 点击 **开始扫描**
4. 等待扫描完成，图片将自动显示在瀑布流画廊中

### 2️⃣ 查看图片详情

- **已入库图片**：在画廊中点击图片，右侧显示完整元数据
- **未入库图片**：切换到 `Image Reader` 标签，拖拽图片即可查看

### 3️⃣ 自动标签

#### 单张图片
1. 在画廊中选择图片
2. 右侧详情工作台点击 **自动标签**

#### 批量处理
1. 左侧 **批量工具** 区域
2. 设置阈值（General / Character）
3. 点击 **批量自动标签**
4. 查看实时进度条

### 4️⃣ 手动分拣

1. 切换到 `Manual Sort` 标签
2. 填写 W / A / S / D 四个目标目录（至少一个）
3. 点击 **开始手动分拣**
4. 使用键盘快捷键操作：
   - `W / A / S / D`：移动到对应目录
   - `Space`：跳过
   - `Z`：撤销

### 5️⃣ 相似图搜索

切换到 `Similar` 标签：
- **使用当前图片**：点击"使用当前选中图片"
- **上传外部图片**：点击"上传外部图片"选择本地文件

### 6️⃣ Prompt Lab

切换到 `Prompt Lab` 标签：
1. 手动输入标签，或点击 **带入当前图片标签**
2. 选择质量预设和计数标签（如 1girl）
3. 点击 **生成 Prompt**
4. 复制生成的正向和负向 Prompt

---

## 🎯 WD14 模型配置（可选）

将以下文件放入 `models/wd14/` 目录：

- `model.onnx`
- `selected_tags.csv`

放置后，顶部状态栏会显示 **自动标签引擎：WD14**

如果不配置模型，系统将自动使用"文件名回退"模式。

---

## 🏗️ 项目结构

```
sd-image-sorter-custom/
├── backend/
│   └── app/
│       ├── main.py              # FastAPI 入口
│       ├── database.py          # 数据库配置
│       ├── models.py            # ORM 模型
│       ├── schemas.py           # Pydantic 模型
│       ├── routers/             # API 路由
│       │   ├── actions.py       # 操作类 API
│       │   ├── images.py        # 图片查询 API
│       │   └── tools.py         # 工具类 API
│       └── services/            # 业务逻辑
│           ├── autotag.py       # 自动标签
│           ├── scanner.py       # 图库扫描
│           ├── similarity.py    # 相似图搜索
│           ├── manual_sort.py   # 手动分拣
│           ├── prompt_lab.py    # Prompt Lab
│           └── wd14.py          # WD14 模型
├── frontend/
│   ├── index.html               # 主页面
│   ├── app.js                   # 瀑布流布局逻辑
│   ├── styles.css               # 主样式
│   └── vs-enhancements.css      # VS Code 主题增强
├── models/
│   └── wd14/                    # WD14 模型目录
├── data/                        # SQLite 数据库
└── docs/                        # 文档和截图
```

---

## 🎨 瀑布流布局技术

本项目采用**纯 JavaScript 实现的瀑布流布局算法**：

### 核心特性
- ✅ **零依赖**：无需 Masonry.js 等外部库
- ✅ **贪心算法**：将每张图片放入当前最短的列
- ✅ **绝对定位**：精确控制每张卡片位置
- ✅ **响应式**：窗口大小改变时自动重排
- ✅ **性能优化**：防抖处理，流畅滚动

### 工作原理
```javascript
// 伪代码示意
1. 初始化 5 列，高度都为 0
2. 对于每张图片：
   a. 找到当前最短的列
   b. 将图片放到该列顶部
   c. 更新该列高度
3. 设置容器总高度 = 最高列的高度
```

详细技术文档：[MASONRY_CHANGES.md](MASONRY_CHANGES.md)

---

## 🔧 技术栈

### 后端
- **FastAPI** - 现代化 Web 框架
- **SQLAlchemy** - ORM 数据库操作
- **SQLite** - 轻量级数据库
- **PIL / Pillow** - 图像处理
- **ONNX Runtime** - WD14 模型推理
- **imagehash** - 感知哈希计算

### 前端
- **原生 JavaScript** - 无框架依赖
- **CSS Grid + Absolute Positioning** - 瀑布流布局
- **VS Code 主题系统** - 深色/浅色主题切换

---

## 📝 更新日志

### v2.0 - 瀑布流增强版 (2026-06-06)

#### 🎨 新增
- **Pinterest 风格瀑布流布局**：5 列自适应布局
- **纯 JavaScript 实现**：移除外部库依赖
- **贪心算法优化**：智能填充最短列
- **响应式设计**：窗口调整时自动重排

#### 🐛 修复
- 修复 CSS Grid 固定高度导致的图片拉伸问题
- 修复 Masonry.js CDN 加载失败问题
- 优化图片加载等待机制

#### 📖 文档
- 新增 [MASONRY_CHANGES.md](MASONRY_CHANGES.md) - 技术实现说明
- 新增 [WATERFALL_TEST.md](WATERFALL_TEST.md) - 测试指南

### v1.0 - 初始版本

- 基础图库管理功能
- 元数据提取
- 自动标签
- 相似图搜索
- Prompt Lab
- 手动分拣模式

---

## ⚠️ 注意事项

1. **图片移动是真实移动**：建议先用测试目录验证功能
2. **批量操作**：批量自动标签是后台任务，前端会显示实时进度
3. **相似图搜索**：当前使用感知哈希，非 CLIP embedding
4. **性能**：大量图片（1000+）加载时需要等待所有图片加载完成才会布局

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发环境搭建

1. Clone 项目
```bash
git clone https://github.com/yourusername/sd-image-sorter-custom.git
cd sd-image-sorter-custom
```

2. 创建虚拟环境
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 启动开发服务器
```bash
uvicorn backend.app.main:app --reload --port 8000
```

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- [WD14 Tagger](https://huggingface.co/SmilingWolf/wd-v1-4-vit-tagger) - 图像标签模型
- [Pillow](https://pillow.readthedocs.io/) - Python 图像处理库
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Web 框架

---

## 📧 联系方式

- Issue: [GitHub Issues](https://github.com/yourusername/sd-image-sorter-custom/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/sd-image-sorter-custom/discussions)

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐️ Star 支持一下！**

Made with ❤️ by [Your Name]

</div>
