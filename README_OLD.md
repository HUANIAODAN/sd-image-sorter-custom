# SD Image Sorter Custom

这是一个本地运行的 SD 图片整理工具，当前这个自定义版已经整合了这些模块：

- `Gallery` 图库扫描、浏览、详情工作台
- 高级筛选：生成器、内容分级、标签、Checkpoint、LoRA、Prompt 关键词、尺寸、长宽比、星级
- 高级排序：最新、最旧、文件名、星级、Prompt 长度、标签数量、生成器、Checkpoint、文件大小
- 元数据提取：`ComfyUI / NovelAI / WebUI / A1111 / Forge`
- `Image Reader`：不入库也能直接拖图读取参数
- `Prompt Lab`：从图库标签和 prompt token 反推可复用 prompt
- `Similar`：基于感知哈希的近似图搜索
- `Manual Sort`：`W / A / S / D` 手动分拣，`Space` 跳过，`Z` 撤销
- 批量自动标签
- 批量移动 / 自动分流

## 快速启动

### Windows PowerShell

```powershell
.\run.ps1
```

### Windows CMD

```bat
run.bat
```

启动后打开：

- 前端：`http://localhost:8000`
- 健康检查：`http://localhost:8000/api/health`

如果 PowerShell 提示脚本执行受限，就直接双击 `run.bat`。

## 怎么使用

### 1. 扫图库

1. 打开 `Gallery`
2. 在左侧 `扫描图库` 输入你的图片目录
3. 点 `开始扫描`

扫描后图片会进入本地数据库，之后就可以筛选、排序、打标、移动。

### 2. 看参数

有两种方式：

- 已扫描入库：在 `Gallery` 里点选图片，右侧就会显示 prompt、negative prompt、checkpoint、LoRA、VAE、seed、steps、CFG、sampler 等
- 未入库图片：切到 `Image Reader`，直接拖图进去

### 3. 自动标签

- 单张：在右侧详情点 `自动标签`
- 批量：左侧 `批量工具` 里点 `批量自动标签`

如果没有放 WD14 模型，系统会自动回退到“按文件名猜标签”模式。

## WD14 模型

把这两个文件放到 `models/wd14/`：

- `models/wd14/model.onnx`
- `models/wd14/selected_tags.csv`

放好以后，顶部状态会从“文件名回退”切到 `WD14`。

## Manual Sort

切到 `Manual Sort`：

1. 先填 `W / A / S / D` 四个目标目录，至少填一个
2. 它会继承你当前 `Gallery` 的筛选条件
3. 点 `开始手动分拣`
4. 用这些键操作：

- `W / A / S / D`：移动到对应目录
- `Space`：跳过
- `Z`：撤销上一步

## Similar

切到 `Similar`：

- 可以直接用当前选中的图库图片搜近似图
- 也可以上传外部图片，在图库里找相似结果

## Prompt Lab

切到 `Prompt Lab`：

- 手工输入标签，或者一键带入当前选中图片的标签
- 可选质量预设、计数标签、负向 prompt
- 也可以让系统从图库里随机补一些标签

## 目录结构

```text
backend/
  app/
    main.py
    database.py
    models.py
    schemas.py
    routers/
      actions.py
      images.py
      tools.py
    services/
      autotag.py
      autotag_jobs.py
      file_ops.py
      manual_sort.py
      metadata.py
      prompt_lab.py
      prompt_translate.py
      query_utils.py
      scanner.py
      similarity.py
      wd14.py
frontend/
  index.html
  app.js
  styles.css
models/
  wd14/
    README.md
```

## 注意事项

- 图片移动是实际移动，建议先拿测试目录试一轮
- 批量自动标签是后台任务，前端会轮询进度
- Similar 当前是感知哈希近似搜索，不是 CLIP embedding 版
- 这个版本还没有接入 YOLO 打码、Artist ID、美学评分这些重模型模块
