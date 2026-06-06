# Git 提交和发布指南

## 📝 提交到 GitHub

### 1. 初始化 Git（如果还没有）

```bash
cd "D:\1.AI\3.SD 图片整理工具\sd-image-sorter-custom-2026-04-22-hotfix"
git init
git add .
git commit -m "feat: v2.0 - 实现 Pinterest 风格瀑布流布局"
```

### 2. 连接到 GitHub 仓库

```bash
# 创建 GitHub 仓库后
git remote add origin https://github.com/yourusername/sd-image-sorter-custom.git
git branch -M main
git push -u origin main
```

### 3. 创建版本标签

```bash
git tag -a v2.0 -m "v2.0 - 瀑布流增强版"
git push origin v2.0
```

## 📦 创建 GitHub Release

### 步骤 1：进入 Releases 页面
访问：`https://github.com/yourusername/sd-image-sorter-custom/releases/new`

### 步骤 2：填写 Release 信息

**Tag version:**
```
v2.0
```

**Release title:**
```
v2.0 - 瀑布流增强版 🎨
```

**Description:**
复制 `GITHUB_RELEASE.md` 的内容

### 步骤 3：上传资产（可选）

如果有截图或演示视频，可以上传：
- `waterfall-demo.gif` - 演示动图
- `screenshot-gallery.png` - 画廊截图
- `screenshot-detail.png` - 详情截图

### 步骤 4：发布

点击 "Publish release" 按钮

## 📋 推荐的 Commit Message 格式

```bash
# 主要更新
git commit -m "feat: 实现 Pinterest 风格 5 列瀑布流布局

- 使用纯 JavaScript 实现，无外部依赖
- 采用贪心算法智能排列图片
- 支持窗口 resize 自动重排
- 添加 0.3s 平滑过渡动画

BREAKING CHANGE: 移除 Masonry.js 依赖"

# 文档更新
git commit -m "docs: 添加瀑布流技术文档和测试指南

- 新增 MASONRY_CHANGES.md
- 新增 WATERFALL_TEST.md
- 新增 RELEASE_NOTES_v2.0.md
- 更新 README.md"

# 样式修复
git commit -m "fix: 修复图片拉伸和布局问题

- 移除 CSS Grid 固定高度
- 改用 absolute 定位
- 优化图片加载逻辑"
```

## 🎯 完整发布流程

```bash
# 1. 添加所有文件
git add .

# 2. 提交更改
git commit -m "feat: v2.0 - 实现 Pinterest 风格瀑布流布局

主要更新：
- 5 列瀑布流布局，纯 JavaScript 实现
- 智能贪心算法，自动填充最短列
- 响应式设计，窗口调整自动重排
- 流畅的 0.3s 过渡动画

修复问题：
- 图片拉伸问题
- CDN 依赖问题
- 布局计算精度

文档：
- MASONRY_CHANGES.md - 技术实现
- WATERFALL_TEST.md - 测试指南
- RELEASE_NOTES_v2.0.md - 完整更新日志
- README_NEW.md - 新版 README

BREAKING CHANGE: 移除 Masonry.js 外部依赖"

# 3. 推送到 GitHub
git push origin main

# 4. 创建标签
git tag -a v2.0 -m "v2.0 - 瀑布流增强版

- Pinterest 风格瀑布流布局
- 纯 JavaScript 实现
- 零外部依赖
- 性能优化"

# 5. 推送标签
git push origin v2.0

# 6. 在 GitHub 上创建 Release（手动）
```

## 🌟 README 文件说明

项目中现在有两个 README：

1. **README.md** - 原始版本（保留）
2. **README_NEW.md** - 新版完整文档（建议使用）

**推荐操作：**
```bash
# 备份原 README
mv README.md README_OLD.md

# 使用新版 README
mv README_NEW.md README.md

# 提交更改
git add README.md README_OLD.md
git commit -m "docs: 更新 README 为完整版文档"
git push
```

## 📸 建议添加的截图

在 `docs/` 目录下添加：

1. **waterfall-demo.gif** - 瀑布流布局演示动图
2. **screenshot-gallery.png** - 画廊视图截图
3. **screenshot-filter.png** - 筛选功能截图
4. **screenshot-detail.png** - 详情工作台截图
5. **screenshot-reader.png** - Image Reader 截图
6. **screenshot-promptlab.png** - Prompt Lab 截图
7. **screenshot-similar.png** - 相似图搜索截图
8. **screenshot-sort.png** - 手动分拣截图

```bash
# 创建 docs 目录
mkdir docs

# 添加截图后
git add docs/
git commit -m "docs: 添加项目截图"
git push
```

## ✅ 发布前检查清单

- [ ] 所有代码已提交
- [ ] 版本号已更新
- [ ] README 已更新
- [ ] 更新日志已完成
- [ ] 测试通过
- [ ] 截图已准备
- [ ] LICENSE 文件已添加
- [ ] .gitignore 已配置
- [ ] requirements.txt 已更新

## 🎉 发布后推广

### 1. 社交媒体
- Twitter/X
- Reddit (r/StableDiffusion)
- Discord 社区

### 2. 技术社区
- V2EX
- 知乎
- 掘金

### 3. 推广文案模板

```
🎨 发布了 SD Image Sorter v2.0 - 瀑布流增强版！

✨ 新功能：
- Pinterest 风格 5 列瀑布流布局
- 纯 JS 实现，零外部依赖
- 智能布局算法，流畅动画

🔗 GitHub: [你的链接]

#StableDiffusion #ImageManagement #OpenSource
```

---

祝发布顺利！🚀
