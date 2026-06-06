# 瀑布流布局测试指南

## 🚀 快速测试步骤

### 1. 清除浏览器缓存
在浏览器中按 `Ctrl + Shift + Delete`，清除缓存的图片和文件

或者使用硬刷新：`Ctrl + F5`

### 2. 启动后端服务
```bash
cd "D:\1.AI\3.SD 图片整理工具\sd-image-sorter-custom-2026-04-22-hotfix"
# 运行你的后端启动命令
```

### 3. 访问前端
打开浏览器访问：http://localhost:你的端口号

### 4. 扫描图库
- 在左侧输入图库目录路径
- 点击"开始扫描"
- 等待扫描完成

### 5. 观察效果
应该看到：
- ✅ 中间区域显示 5 列图片
- ✅ 图片高度各不相同（根据原图比例）
- ✅ 图片紧密排列，像砖墙一样错落有致
- ✅ 没有大块空白区域

## 🔍 调试检查清单

如果布局不正常，请检查：

### 检查 1：打开浏览器开发者工具（F12）
查看 Console 标签，是否有红色错误信息

### 检查 2：查看 Network 标签
- 确认 `app.js?v=13` 已加载（状态码 200）
- 确认 `styles.css?v=21` 已加载（状态码 200）
- 确认 `vs-enhancements.css?v=21` 已加载（状态码 200）

### 检查 3：查看 Elements 标签
选中一个图片卡片（.thumb-card），在右侧 Styles 面板检查：
- 是否有 `position: absolute`
- 是否有 `left` 和 `top` 的像素值（如 `left: 200px`, `top: 150px`）
- 是否有 `width` 的像素值

### 检查 4：查看容器
选中 `.image-grid` 容器，检查：
- 是否有 `position: relative`
- 是否有 `height` 的像素值（如 `height: 3000px`）

## 🎨 预期的 DOM 结构

```html
<div class="image-grid" style="position: relative; height: 3000px;">
  <button class="thumb-card" style="position: absolute; left: 0px; top: 0px; width: 200px;">
    <img class="thumb-image" src="..." />
    <div class="thumb-body">...</div>
  </button>
  <button class="thumb-card" style="position: absolute; left: 208px; top: 0px; width: 200px;">
    ...
  </button>
  <!-- 更多卡片... -->
</div>
```

## 📐 工作原理示意

```
第1列  第2列  第3列  第4列  第5列
[图1] [图2] [图3] [图4] [图5]
       [图6] [图7]       [图8]
[图9]        [图10][图11]
       [图12]      [图13]
[图14][图15]      [图16][图17]
...
```

算法会：
1. 将图1-5放到5列的顶部
2. 图6放到最短的列（假设是第2列）
3. 图7放到最短的列（假设是第3列）
4. 以此类推...

## ⚠️ 常见问题

### 问题：图片不显示
**原因：** 图片路径错误或图片加载失败
**解决：** 检查 Network 标签，查看图片请求是否 404

### 问题：图片全部堆叠在左上角
**原因：** JavaScript 未执行或出错
**解决：** 
1. 检查 Console 是否有错误
2. 确认 app.js 已正确加载
3. 确认图片已加载完成

### 问题：图片排成一行
**原因：** CSS 未正确加载
**解决：** 
1. 硬刷新浏览器（Ctrl + F5）
2. 检查 styles.css 版本号是否为 v=21
3. 检查 .thumb-card 是否有 position: absolute

### 问题：调整窗口大小后布局错乱
**原因：** resize 事件监听器可能未正确绑定
**解决：** 刷新页面

## 📊 性能提示

- 第一次加载时，需要等待所有图片加载完成才会布局
- 如果图片很多（>100张），可能需要几秒钟
- 可以在 Console 中输入 `document.querySelectorAll('.thumb-card').length` 查看卡片数量

## 🎯 成功标志

当你看到这样的效果时，说明成功了：
- 5列图片整齐排列
- 每列的图片紧密相连，没有大间隙
- 不同列的高度不完全一样（因为图片高度不同）
- 滚动流畅，没有性能问题
- 调整窗口大小后自动重新布局

祝测试顺利！🎉
