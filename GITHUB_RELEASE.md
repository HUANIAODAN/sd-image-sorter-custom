# v2.0 - 瀑布流增强版 🎨

## 🌟 重大更新

### Pinterest 风格瀑布流布局

全新的 5 列瀑布流画廊视图，让你的图片以最优雅的方式呈现！

![Waterfall Layout Demo](docs/waterfall-demo.gif)

## ✨ 新功能

- 🖼️ **5 列瀑布流布局** - 图片按原始比例展示，自动填充最短列
- 🚀 **纯 JavaScript 实现** - 零外部依赖，加载更快
- 🎯 **智能布局算法** - 贪心算法确保紧凑排列
- 📱 **响应式设计** - 窗口大小改变时自动重排
- ✨ **流畅动画** - 0.3s 平滑过渡效果

## 🔧 技术亮点

```javascript
// 核心算法
初始化 5 列 → 找最短列 → 放置图片 → 更新高度 → 重复
```

- **O(n) 时间复杂度** - 高效布局计算
- **绝对定位** - 精确控制每张卡片
- **防抖优化** - resize 事件 250ms 防抖

## 🐛 修复

- ✅ 修复 CSS Grid 导致的图片拉伸问题
- ✅ 移除 Masonry.js CDN 依赖问题
- ✅ 优化图片加载等待机制
- ✅ 提升布局计算性能

## 📊 性能提升

- **加载速度** ⚡ 减少外部库请求
- **渲染性能** 📈 优化布局算法
- **内存占用** 💾 更轻量的实现

## 📖 文档

- [技术实现说明](MASONRY_CHANGES.md)
- [测试指南](WATERFALL_TEST.md)
- [完整更新日志](RELEASE_NOTES_v2.0.md)

## 🚀 快速开始

```bash
# Windows
run.bat

# Linux/macOS
./run.sh

# 访问
http://localhost:8000
```

## ⚠️ 升级提示

**首次使用请清除浏览器缓存：** `Ctrl + F5` 或 `Ctrl + Shift + Delete`

## 📦 完整功能列表

- ✅ 瀑布流画廊
- ✅ 高级筛选排序
- ✅ 元数据提取（ComfyUI/NovelAI/WebUI/Forge）
- ✅ WD14 自动标签
- ✅ 相似图搜索
- ✅ Prompt Lab
- ✅ 快捷键分拣模式
- ✅ Image Reader

## 🤝 参与贡献

欢迎提交 Issue 和 PR！

## 📝 更新内容

### Added
- Pinterest 风格 5 列瀑布流布局
- 纯 JavaScript 布局算法
- 窗口 resize 自动重排
- 平滑过渡动画

### Changed
- 移除 Masonry.js 依赖
- 优化图片加载逻辑
- 重构网格渲染函数

### Fixed
- 图片宽高比保持
- 布局计算精度
- CDN 加载可靠性

---

<div align="center">

**如果觉得有用，请给个 ⭐️ Star！**

[下载源码](https://github.com/yourusername/sd-image-sorter-custom/archive/refs/tags/v2.0.zip) | [查看文档](README.md) | [报告问题](https://github.com/yourusername/sd-image-sorter-custom/issues)

</div>
