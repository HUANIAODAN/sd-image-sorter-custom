const state = {
  view: "gallery",
  page: 1,
  pageSize: 60,
  total: 0,
  currentItems: [],
  selectedImageId: null,
  currentDetail: null,
  libraries: {
    tags: [],
    generators: [],
    checkpoints: [],
    loras: [],
  },
  galleries: [],
  batchJobId: null,
  batchPollTimer: null,
  readerObjectUrl: null,
  similarObjectUrl: null,
  manualSortActive: false,
  promptLabLibrary: null,
};

const els = {};

function byId(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function isTypingElement(target) {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

async function api(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  const fetchOptions = { method: "GET", ...options, headers };

  if (fetchOptions.body && !(fetchOptions.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, fetchOptions);
  if (!response.ok) {
    let message = `请求失败 (${response.status})`;
    try {
      const payload = await response.json();
      message = payload.detail || payload.error || message;
    } catch {
      try {
        message = await response.text();
      } catch {
        // Keep fallback.
      }
    }
    throw new Error(message);
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function qs(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  });
  const text = query.toString();
  return text ? `?${text}` : "";
}

function setStatus(element, message, isError = false) {
  element.textContent = message || "";
  element.classList.toggle("is-error", Boolean(isError));
}

function clearObjectUrl(key) {
  const value = state[key];
  if (value) {
    URL.revokeObjectURL(value);
    state[key] = null;
  }
}

function switchView(view) {
  state.view = view;
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("is-active", tab.dataset.view === view);
  });
  document.querySelectorAll(".view").forEach((panel) => {
    panel.classList.toggle("is-active", panel.id === `view-${view}`);
  });
}

function parseListInput(value) {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function getFilterState() {
  return {
    keyword: els.keyword.value.trim(),
    prompt_keyword: els.promptKeyword.value.trim(),
    tag: els.filterTag.value.trim(),
    generator: els.filterGenerator.value.trim(),
    content_rating: els.filterContentRating.value.trim(),
    checkpoint: els.filterCheckpoint.value.trim(),
    lora: els.filterLora.value.trim(),
    min_rating: els.minRating.value.trim(),
    max_rating: els.maxRating.value.trim(),
    min_width: els.minWidth.value.trim(),
    max_width: els.maxWidth.value.trim(),
    min_height: els.minHeight.value.trim(),
    max_height: els.maxHeight.value.trim(),
    aspect_ratio: els.aspectRatio.value,
    sort_by: els.sortBy.value,
  };
}

function resetFilters() {
  [
    els.keyword,
    els.promptKeyword,
    els.filterTag,
    els.filterGenerator,
    els.filterContentRating,
    els.filterCheckpoint,
    els.filterLora,
    els.minRating,
    els.maxRating,
    els.minWidth,
    els.maxWidth,
    els.minHeight,
    els.maxHeight,
  ].forEach((input) => {
    input.value = "";
  });
  els.aspectRatio.value = "";
  els.sortBy.value = "newest";
}

function getSelectedItem() {
  if (!state.selectedImageId) {
    return null;
  }
  return state.currentItems.find((item) => item.id === state.selectedImageId) || null;
}

function buildBadge(label, tone = "") {
  return `<span class="badge ${tone}">${escapeHtml(label)}</span>`;
}

function renderGrid(target, items, options = {}) {
  const { showDistance = false } = options;
  target.innerHTML = "";
  if (!items.length) {
    target.innerHTML = `<div class="card"><p class="muted">暂无数据</p></div>`;
    return;
  }

  items.forEach((item) => {
    const image = item.image || item;
    const node = els.thumbTemplate.content.firstElementChild.cloneNode(true);
    node.dataset.imageId = String(image.id);
    if (image.id === state.selectedImageId && target === els.imageGrid) {
      node.classList.add("is-selected");
    }

    const img = node.querySelector(".thumb-image");
    img.src = `/api/images/${image.id}/preview`;
    img.alt = image.name;

    node.querySelector(".thumb-name").textContent = image.name;
    const parts = [
      `★${image.rating}`,
      image.generator_source || "Unknown",
      image.content_rating || "unknown",
    ];
    if (showDistance) {
      parts.push(`sim ${(item.score * 100).toFixed(1)}%`);
    }
    node.querySelector(".thumb-meta").textContent = parts.join(" | ");

    node.addEventListener("click", () => {
      if (target === els.imageGrid) {
        selectImage(image.id);
        return;
      }
      state.selectedImageId = image.id;
      switchView("gallery");
      loadImages(image.id);
    });
    target.appendChild(node);
  });

  // Initialize waterfall layout after images are loaded
  initWaterfallLayout(target);
}

async function loadLibraries() {
  const [tags, generators, checkpoints, loras, galleries] = await Promise.all([
    api("/api/meta/tags?limit=200"),
    api("/api/meta/generators"),
    api("/api/meta/checkpoints?limit=200"),
    api("/api/meta/loras?limit=200"),
    api("/api/galleries"),
  ]);

  state.libraries.tags = tags.items || [];
  state.libraries.generators = generators.items || [];
  state.libraries.checkpoints = checkpoints.items || [];
  state.libraries.loras = loras.items || [];
  state.galleries = galleries.items || [];

  fillDataList("tagOptions", state.libraries.tags);
  fillDataList("generatorOptions", state.libraries.generators);
  fillDataList("checkpointOptions", state.libraries.checkpoints);
  fillDataList("loraOptions", state.libraries.loras);
  renderGalleryList();
}

function fillDataList(id, items) {
  const list = byId(id);
  list.innerHTML = items.map((item) => `<option value="${escapeHtml(item.value)}"></option>`).join("");
}

function renderGalleryList() {
  els.galleryList.innerHTML = "";
  if (!state.galleries.length) {
    els.galleryList.innerHTML = `<p class="muted">还没有扫描任何图库</p>`;
    return;
  }
  state.galleries.forEach((gallery) => {
    const breakdown = Object.entries(gallery.generator_breakdown || {})
      .map(([name, count]) => `${name}: ${count}`)
      .join(" | ");
    const node = document.createElement("button");
    node.type = "button";
    node.className = "library-item";
    node.innerHTML = `
      <strong>${escapeHtml(gallery.name)}</strong>
      <div class="muted">${escapeHtml(gallery.path)}</div>
      <div class="muted">${gallery.image_count} 张${breakdown ? ` | ${escapeHtml(breakdown)}` : ""}</div>
    `;
    node.addEventListener("click", () => {
      els.scanDir.value = gallery.path;
      setStatus(els.detailStatus, `已带入图库目录：${gallery.path}`);
    });
    els.galleryList.appendChild(node);
  });
}

async function updateModelRuntimeBadge() {
  try {
    const runtime = await api("/api/auto-tag/runtime");
    els.modelBadge.textContent =
      runtime.mode === "wd14" ? "自动标签引擎：WD14" : `自动标签引擎：文件名回退 (${runtime.detail})`;
  } catch (error) {
    els.modelBadge.textContent = `自动标签引擎状态获取失败：${error.message}`;
  }
}

async function loadImages(preferredId = state.selectedImageId) {
  const filters = getFilterState();
  els.reloadBtn.disabled = true;
  try {
    const data = await api(
      `/api/images${qs({
        page: state.page,
        page_size: state.pageSize,
        ...filters,
      })}`
    );
    state.total = data.total;
    state.currentItems = data.items;
    if (!state.currentItems.length) {
      state.selectedImageId = null;
      state.currentDetail = null;
    } else if (state.currentItems.some((item) => item.id === preferredId)) {
      state.selectedImageId = preferredId;
    } else {
      state.selectedImageId = state.currentItems[0].id;
    }

    renderGrid(els.imageGrid, state.currentItems);
    const maxPage = Math.max(1, Math.ceil(state.total / state.pageSize));
    els.pageInfo.textContent = `第 ${state.page} / ${maxPage} 页`;
    els.resultSummary.textContent = `共 ${state.total} 张，当前页 ${state.currentItems.length} 张`;
    els.galleryStats.textContent = `${state.total} 张图片`;
    els.prevPage.disabled = state.page <= 1;
    els.nextPage.disabled = state.page >= maxPage;

    if (state.selectedImageId) {
      await loadDetail(state.selectedImageId);
    } else {
      renderDetail(null);
    }
  } catch (error) {
    setStatus(els.detailStatus, error.message, true);
    els.imageGrid.innerHTML = `<div class="card"><p class="muted">${escapeHtml(error.message)}</p></div>`;
  } finally {
    els.reloadBtn.disabled = false;
  }
}

async function loadDetail(imageId) {
  const token = imageId;
  try {
    const detail = await api(`/api/images/${imageId}`);
    if (state.selectedImageId !== token) {
      return;
    }
    state.currentDetail = detail;
    renderDetail(detail);
  } catch (error) {
    if (state.selectedImageId === token) {
      setStatus(els.detailStatus, error.message, true);
    }
  }
}

function selectImage(imageId) {
  state.selectedImageId = imageId;
  renderGrid(els.imageGrid, state.currentItems);
  loadDetail(imageId);
}

function renderDetail(detail) {
  if (!detail) {
    els.detailHint.textContent = "请选择图片";
    els.detailPreview.removeAttribute("src");
    els.detailName.textContent = "未选择图片";
    els.detailPath.textContent = "-";
    els.detailMeta.textContent = "-";
    els.detailModelMeta.textContent = "-";
    els.detailBadges.innerHTML = "";
    els.detailCheckpoint.textContent = "(暂无)";
    els.detailLora.textContent = "(暂无)";
    els.detailPrompt.textContent = "(暂无)";
    els.detailNegative.textContent = "(暂无)";
    els.detailTagInput.value = "";
    els.detailRatingInput.value = "";
    return;
  }

  els.detailHint.textContent = `#${detail.id}`;
  els.detailPreview.src = `/api/images/${detail.id}/preview`;
  els.detailName.textContent = detail.name;
  els.detailPath.textContent = detail.path;
  const sizeKb = (detail.size_bytes / 1024).toFixed(1);
  els.detailMeta.textContent = `${detail.width || "?"} × ${detail.height || "?"} | ${sizeKb} KB | ${detail.generator_source} | ${detail.content_rating}`;
  els.detailModelMeta.textContent = `Checkpoint: ${detail.checkpoint_name || "-"} | LoRA: ${detail.lora_names.join(", ") || "-"} | VAE: ${detail.vae_name || "-"} | Seed: ${detail.seed || "-"}`;
  els.detailBadges.innerHTML = [
    buildBadge(`★ ${detail.rating}`),
    detail.steps ? buildBadge(`steps ${detail.steps}`) : "",
    detail.cfg_scale ? buildBadge(`cfg ${detail.cfg_scale}`) : "",
    detail.sampler ? buildBadge(detail.sampler) : "",
    detail.schedule_type ? buildBadge(detail.schedule_type) : "",
    detail.clip_skip ? buildBadge(`clip ${detail.clip_skip}`) : "",
  ].join("");
  els.detailCheckpoint.textContent = detail.checkpoint_name || "(暂无)";
  els.detailLora.textContent = detail.lora_names && detail.lora_names.length > 0 ? detail.lora_names.join(", ") : "(暂无)";
  els.detailPrompt.textContent = detail.positive_prompt || "(暂无)";
  els.detailNegative.textContent = detail.negative_prompt || "(暂无)";
  els.detailTagInput.value = detail.tags.join(", ");
  els.detailRatingInput.value = String(detail.rating ?? "");
}

async function scanGallery() {
  const directory = els.scanDir.value.trim();
  if (!directory) {
    setStatus(els.detailStatus, "请先输入扫描目录", true);
    return;
  }
  els.scanBtn.disabled = true;
  els.scanResult.textContent = "扫描中...";
  try {
    const maxValue = els.scanMax.value ? Number(els.scanMax.value) : null;
    const result = await api("/api/scan", {
      method: "POST",
      body: JSON.stringify({
        directory,
        recursive: els.scanRecursive.checked,
        max_files: Number.isFinite(maxValue) ? maxValue : null,
      }),
    });
    els.scanResult.textContent = JSON.stringify(result, null, 2);
    state.page = 1;
    await Promise.all([loadLibraries(), loadImages()]);
    setStatus(els.detailStatus, "扫描完成");
  } catch (error) {
    els.scanResult.textContent = error.message;
    setStatus(els.detailStatus, error.message, true);
  } finally {
    els.scanBtn.disabled = false;
  }
}

async function saveTags() {
  const item = getSelectedItem();
  if (!item) {
    setStatus(els.detailStatus, "请先选择图片", true);
    return;
  }
  const tags = parseListInput(els.detailTagInput.value);
  await api(`/api/images/${item.id}/tags`, {
    method: "POST",
    body: JSON.stringify({ tags }),
  });
  setStatus(els.detailStatus, "标签已保存");
  await Promise.all([loadImages(item.id), loadLibraries()]);
}

async function saveRating() {
  const item = getSelectedItem();
  if (!item) {
    setStatus(els.detailStatus, "请先选择图片", true);
    return;
  }
  const rating = Number(els.detailRatingInput.value);
  if (!Number.isFinite(rating) || rating < 0 || rating > 5) {
    setStatus(els.detailStatus, "星级必须在 0 到 5 之间", true);
    return;
  }
  await api(`/api/images/${item.id}/rating`, {
    method: "POST",
    body: JSON.stringify({ rating }),
  });
  setStatus(els.detailStatus, "星级已保存");
  await loadImages(item.id);
}

async function autoTagCurrent() {
  const item = getSelectedItem();
  if (!item) {
    setStatus(els.detailStatus, "请先选择图片", true);
    return;
  }
  try {
    const result = await api("/api/auto-tag", {
      method: "POST",
      body: JSON.stringify({ image_id: item.id }),
    });
    setStatus(els.detailStatus, `自动标签完成，模式：${result.source}，内容分级：${result.content_rating || "unknown"}`);
    await Promise.all([loadImages(item.id), loadLibraries(), updateModelRuntimeBadge()]);
  } catch (error) {
    setStatus(els.detailStatus, error.message, true);
  }
}

async function moveCurrentImage() {
  const item = getSelectedItem();
  if (!item) {
    setStatus(els.detailStatus, "请先选择图片", true);
    return;
  }
  const targetDirectory = els.detailTargetDir.value.trim();
  if (!targetDirectory) {
    setStatus(els.detailStatus, "请输入移动目标目录", true);
    return;
  }
  try {
    const result = await api("/api/move", {
      method: "POST",
      body: JSON.stringify({
        image_id: item.id,
        target_directory: targetDirectory,
        strategy: els.detailMoveStrategy.value,
      }),
    });
    setStatus(els.detailStatus, `已移动到：${result.new_path}`);
    await loadImages();
  } catch (error) {
    setStatus(els.detailStatus, error.message, true);
  }
}

async function startBatchAutoTag() {
  if (state.batchPollTimer) {
    setStatus(els.batchMoveStatus, "已有批量任务在运行", true);
    return;
  }
  try {
    els.batchAutoTagBtn.disabled = true;
    els.batchProgressText.textContent = "正在启动批量任务...";
    const result = await api("/api/auto-tag/batch", {
      method: "POST",
      body: JSON.stringify({
        only_untagged: els.batchOnlyUntagged.checked,
        general_threshold: Number(els.batchGeneralThreshold.value || 0.35),
        character_threshold: Number(els.batchCharacterThreshold.value || 0.85),
      }),
    });
    state.batchJobId = result.job_id;
    setStatus(els.batchMoveStatus, `批量任务已启动，模式：${result.mode}`);
    state.batchPollTimer = setInterval(pollBatchJobStatus, 1000);
    await pollBatchJobStatus();
  } catch (error) {
    els.batchAutoTagBtn.disabled = false;
    els.batchProgressText.textContent = "启动失败";
    setStatus(els.batchMoveStatus, error.message, true);
  }
}

async function pollBatchJobStatus() {
  if (!state.batchJobId) {
    return;
  }
  try {
    const data = await api(`/api/auto-tag/batch/${state.batchJobId}`);
    els.batchProgressFill.style.width = `${Math.max(0, Math.min(data.progress, 100))}%`;
    els.batchProgressText.textContent = `状态: ${data.status} | ${data.processed}/${data.total} | 成功 ${data.success} | 失败 ${data.failed} | 跳过 ${data.skipped}`;
    if (data.status === "completed" || data.status === "failed") {
      clearInterval(state.batchPollTimer);
      state.batchPollTimer = null;
      state.batchJobId = null;
      els.batchAutoTagBtn.disabled = false;
      await Promise.all([loadImages(), loadLibraries(), updateModelRuntimeBadge()]);
    }
  } catch (error) {
    clearInterval(state.batchPollTimer);
    state.batchPollTimer = null;
    state.batchJobId = null;
    els.batchAutoTagBtn.disabled = false;
    setStatus(els.batchMoveStatus, error.message, true);
  }
}

async function batchMoveCurrentFilter() {
  const targetDirectory = els.batchMoveTargetDir.value.trim();
  if (!targetDirectory) {
    setStatus(els.batchMoveStatus, "请输入批量移动目标目录", true);
    return;
  }

  try {
    const result = await api("/api/batch-move", {
      method: "POST",
      body: JSON.stringify({
        ...getFilterState(),
        target_directory: targetDirectory,
        strategy: els.batchMoveStrategy.value,
      }),
    });
    setStatus(els.batchMoveStatus, `批量移动完成：请求 ${result.requested}，成功 ${result.moved}，失败 ${result.errors.length}`);
    await loadImages();
  } catch (error) {
    setStatus(els.batchMoveStatus, error.message, true);
  }
}

function bindReaderDropZone() {
  const activate = (active) => els.readerDropZone.classList.toggle("is-dragover", active);
  ["dragenter", "dragover"].forEach((eventName) => {
    els.readerDropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      activate(true);
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    els.readerDropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      activate(false);
    });
  });
  els.readerDropZone.addEventListener("drop", (event) => {
    const file = event.dataTransfer?.files?.[0];
    if (file) {
      parseReaderFile(file);
    }
  });
}

async function parseReaderFile(file) {
  clearObjectUrl("readerObjectUrl");
  state.readerObjectUrl = URL.createObjectURL(file);
  els.readerPreview.src = state.readerObjectUrl;
  setStatus(els.readerStatus, "读取中...");
  try {
    const formData = new FormData();
    formData.append("file", file);
    const result = await api("/api/reader/parse", {
      method: "POST",
      body: formData,
    });
    renderReaderResult(file.name, result);
    setStatus(els.readerStatus, "读取完成");
  } catch (error) {
    setStatus(els.readerStatus, error.message, true);
  }
}

function renderReaderResult(filename, data) {
  els.readerTitle.textContent = filename;
  els.readerInfo.textContent = `${data.width || "?"} × ${data.height || "?"} | ${(data.size_bytes / 1024).toFixed(1)} KB | ${data.generator_source}`;
  els.readerBadges.innerHTML = [
    buildBadge(data.checkpoint_name || "无 checkpoint"),
    ...(data.lora_names || []).slice(0, 6).map((name) => buildBadge(name)),
  ].join("");
  els.readerPrompt.textContent = data.positive_prompt || "(暂无)";
  els.readerNegative.textContent = data.negative_prompt || "(暂无)";
  const params = [
    data.steps ? `steps: ${data.steps}` : "",
    data.cfg_scale ? `cfg_scale: ${data.cfg_scale}` : "",
    data.sampler ? `sampler: ${data.sampler}` : "",
    data.schedule_type ? `schedule_type: ${data.schedule_type}` : "",
    data.clip_skip ? `clip_skip: ${data.clip_skip}` : "",
    data.seed ? `seed: ${data.seed}` : "",
    data.vae_name ? `vae: ${data.vae_name}` : "",
    data.phash ? `phash: ${data.phash}` : "",
  ]
    .filter(Boolean)
    .join("\n");
  els.readerParams.textContent = params || "(暂无)";
  els.readerMetadata.textContent = JSON.stringify(data.metadata, null, 2);
}

async function loadPromptLabLibrary() {
  try {
    const data = await api("/api/prompt-lab/library?limit=160");
    state.promptLabLibrary = data;
    renderPromptLabLibrary(data);
  } catch (error) {
    setStatus(els.promptLabStatus, error.message, true);
  }
}

function renderPromptLabLibrary(data) {
  els.promptLabTags.innerHTML = (data.tags || [])
    .slice(0, 60)
    .map((item) => `<button type="button" class="chip" data-chip-tag="${escapeHtml(item.value)}">${escapeHtml(item.value)} <span class="muted">${item.count}</span></button>`)
    .join("");

  const renderColumn = (title, items) => `
    <div class="library-col">
      <h3>${escapeHtml(title)}</h3>
      <ul>
        ${(items || [])
          .slice(0, 20)
          .map(
            (item) =>
              `<li><button type="button" class="btn btn-ghost btn-small full prompt-pick" data-prompt-tag="${escapeHtml(item.value)}">${escapeHtml(item.value)} <span class="muted">${item.count}</span></button></li>`
          )
          .join("")}
      </ul>
    </div>
  `;

  els.promptLabLibrary.innerHTML = [
    renderColumn("Top Tags", data.tags),
    renderColumn("Prompt Tokens", data.prompts),
    renderColumn("LoRAs", data.loras),
  ].join("");

  document.querySelectorAll("[data-chip-tag], [data-prompt-tag]").forEach((button) => {
    button.addEventListener("click", () => appendPromptLabTag(button.dataset.chipTag || button.dataset.promptTag));
  });
}

function appendPromptLabTag(tag) {
  const existing = parseListInput(els.promptSelectedTags.value);
  if (!existing.includes(tag)) {
    existing.push(tag);
  }
  els.promptSelectedTags.value = existing.join(", ");
}

async function generatePrompt() {
  try {
    const data = await api("/api/prompt-lab/generate", {
      method: "POST",
      body: JSON.stringify({
        selected_tags: parseListInput(els.promptSelectedTags.value),
        quality_preset: els.promptQuality.value,
        count_tag: els.promptCountTag.value.trim() || "1girl",
        include_negative: els.promptIncludeNegative.checked,
        randomize: els.promptRandomize.checked,
      }),
    });
    els.generatedPrompt.value = data.positive_prompt || "";
    els.generatedNegative.value = data.negative_prompt || "";
    setStatus(els.promptLabStatus, `已生成，使用标签 ${data.tags_used.length} 个`);
  } catch (error) {
    setStatus(els.promptLabStatus, error.message, true);
  }
}

function useCurrentImageTags() {
  const detail = state.currentDetail;
  if (!detail) {
    setStatus(els.promptLabStatus, "当前没有选中图片", true);
    return;
  }
  els.promptSelectedTags.value = detail.tags.join(", ");
  switchView("prompt-lab");
}

async function loadSimilarForSelected() {
  const detail = state.currentDetail;
  if (!detail) {
    setStatus(els.similarStatus, "请先在 Gallery 里选择图片", true);
    return;
  }
  clearObjectUrl("similarObjectUrl");
  els.similarSourcePreview.src = `/api/images/${detail.id}/preview`;
  els.similarSourceInfo.textContent = `${detail.name} | ${detail.generator_source} | ${detail.content_rating}`;
  setStatus(els.similarStatus, "正在查找相似图...");
  try {
    const data = await api(`/api/images/${detail.id}/similar?limit=24`);
    renderGrid(els.similarGrid, data.items || [], { showDistance: true });
    els.similarResultInfo.textContent = `找到 ${(data.items || []).length} 张近似图`;
    setStatus(els.similarStatus, "相似图检索完成");
  } catch (error) {
    setStatus(els.similarStatus, error.message, true);
  }
}

async function loadSimilarForUpload(file) {
  clearObjectUrl("similarObjectUrl");
  state.similarObjectUrl = URL.createObjectURL(file);
  els.similarSourcePreview.src = state.similarObjectUrl;
  els.similarSourceInfo.textContent = file.name;
  setStatus(els.similarStatus, "正在查找相似图...");
  try {
    const formData = new FormData();
    formData.append("file", file);
    const data = await api("/api/similar/upload?limit=24", {
      method: "POST",
      body: formData,
    });
    renderGrid(els.similarGrid, data.items || [], { showDistance: true });
    els.similarResultInfo.textContent = `找到 ${(data.items || []).length} 张近似图`;
    setStatus(els.similarStatus, "相似图检索完成");
  } catch (error) {
    setStatus(els.similarStatus, error.message, true);
  }
}

function renderManualSort(payload) {
  if (payload.done) {
    state.manualSortActive = false;
    els.manualSortTitle.textContent = "分拣完成";
    els.manualSortInfo.textContent = "当前会话已经结束";
    els.manualSortTags.innerHTML = "";
    els.manualSortPreview.removeAttribute("src");
    els.manualSortProgress.textContent = `已完成 | 分拣 ${payload.sorted_count || 0} | 跳过 ${payload.skipped_count || 0}`;
    setStatus(els.manualSortStatus, "分拣完成");
    return;
  }

  state.manualSortActive = true;
  const image = payload.image;
  els.manualSortPreview.src = `/api/images/${image.id}/preview`;
  els.manualSortTitle.textContent = image.name;
  els.manualSortInfo.textContent = `${payload.index + 1} / ${payload.total} | 剩余 ${payload.remaining} | 已分拣 ${payload.sorted_count || 0} | 跳过 ${payload.skipped_count || 0}`;
  els.manualSortTags.innerHTML = (image.tags || []).slice(0, 12).map((tag) => buildBadge(tag)).join("");
  els.manualSortProgress.textContent = `索引 ${payload.index + 1} / ${payload.total}`;
}

async function startManualSort() {
  const folders = {
    w: els.sortFolderW.value.trim(),
    a: els.sortFolderA.value.trim(),
    s: els.sortFolderS.value.trim(),
    d: els.sortFolderD.value.trim(),
  };
  try {
    const payload = await api("/api/manual-sort/start", {
      method: "POST",
      body: JSON.stringify({
        ...getFilterState(),
        folders,
      }),
    });
    renderManualSort(payload);
    setStatus(els.manualSortStatus, "手动分拣已开始");
    switchView("sorting");
  } catch (error) {
    setStatus(els.manualSortStatus, error.message, true);
  }
}

async function manualSortAction(action, folderKey = null) {
  if (!state.manualSortActive && action !== "undo") {
    setStatus(els.manualSortStatus, "请先开始手动分拣", true);
    return;
  }
  try {
    const payload = await api("/api/manual-sort/action", {
      method: "POST",
      body: JSON.stringify({ action, folder_key: folderKey }),
    });
    if (payload.error) {
      setStatus(els.manualSortStatus, payload.error, true);
      return;
    }
    renderManualSort(payload);
    if (!payload.done) {
      setStatus(
        els.manualSortStatus,
        action === "move" ? `已移动到 ${String(folderKey).toUpperCase()}` : action === "skip" ? "已跳过当前图片" : "已撤销上一步"
      );
    }
    await loadImages();
  } catch (error) {
    setStatus(els.manualSortStatus, error.message, true);
  }
}

async function clearManualSort() {
  try {
    await api("/api/manual-sort/session", { method: "DELETE" });
    state.manualSortActive = false;
    els.manualSortTitle.textContent = "等待开始";
    els.manualSortInfo.textContent = "-";
    els.manualSortTags.innerHTML = "";
    els.manualSortPreview.removeAttribute("src");
    els.manualSortProgress.textContent = "未开始";
    setStatus(els.manualSortStatus, "手动分拣会话已清空");
  } catch (error) {
    setStatus(els.manualSortStatus, error.message, true);
  }
}

function initWaterfallLayout(target) {
  const images = target.querySelectorAll('.thumb-image');
  const totalImages = images.length;

  if (totalImages === 0) {
    return;
  }

  let loadedCount = 0;

  const layoutWaterfall = () => {
    // Calculate column heights for waterfall layout
    const cards = target.querySelectorAll('.thumb-card');
    const columns = 5;
    const gap = 8;
    const containerWidth = target.offsetWidth - 32; // minus padding
    const columnWidth = (containerWidth - (gap * (columns - 1))) / columns;

    // Initialize column heights
    const columnHeights = new Array(columns).fill(0);

    cards.forEach((card, index) => {
      // Find shortest column
      let shortestCol = 0;
      let minHeight = columnHeights[0];

      for (let i = 1; i < columns; i++) {
        if (columnHeights[i] < minHeight) {
          minHeight = columnHeights[i];
          shortestCol = i;
        }
      }

      // Position card
      const left = shortestCol * (columnWidth + gap);
      const top = columnHeights[shortestCol];

      card.style.position = 'absolute';
      card.style.left = left + 'px';
      card.style.top = top + 'px';
      card.style.width = columnWidth + 'px';

      // Update column height
      columnHeights[shortestCol] += card.offsetHeight + gap;
    });

    // Set container height
    const maxHeight = Math.max(...columnHeights);
    target.style.height = maxHeight + 'px';
    target.style.position = 'relative';
  };

  const checkAllLoaded = () => {
    loadedCount++;
    if (loadedCount === totalImages) {
      // Small delay to ensure all layouts are complete
      setTimeout(layoutWaterfall, 50);
    }
  };

  // Wait for all images to load
  images.forEach((img) => {
    if (img.complete) {
      checkAllLoaded();
    } else {
      img.addEventListener('load', checkAllLoaded);
      img.addEventListener('error', checkAllLoaded);
    }
  });

  // Re-layout on window resize
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (target.querySelector('.thumb-card')) {
        layoutWaterfall();
      }
    }, 250);
  });
}

function bindEvents() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => switchView(tab.dataset.view));
  });

  els.scanBtn.addEventListener("click", scanGallery);
  els.applyFilterBtn.addEventListener("click", async () => {
    state.page = 1;
    await loadImages();
  });
  els.resetFiltersBtn.addEventListener("click", async () => {
    resetFilters();
    state.page = 1;
    await loadImages();
  });
  els.reloadBtn.addEventListener("click", () => loadImages());
  els.prevPage.addEventListener("click", async () => {
    if (state.page > 1) {
      state.page -= 1;
      await loadImages();
    }
  });
  els.nextPage.addEventListener("click", async () => {
    const maxPage = Math.max(1, Math.ceil(state.total / state.pageSize));
    if (state.page < maxPage) {
      state.page += 1;
      await loadImages();
    }
  });

  els.saveTagsBtn.addEventListener("click", saveTags);
  els.saveRatingBtn.addEventListener("click", saveRating);
  els.autoTagsBtn.addEventListener("click", autoTagCurrent);
  els.moveBtn.addEventListener("click", moveCurrentImage);
  els.batchAutoTagBtn.addEventListener("click", startBatchAutoTag);
  els.batchMoveBtn.addEventListener("click", batchMoveCurrentFilter);
  els.openSimilarBtn.addEventListener("click", async () => {
    switchView("similar");
    await loadSimilarForSelected();
  });

  els.readerDropZone.addEventListener("click", () => els.readerFileInput.click());
  els.readerFileInput.addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    if (file) {
      parseReaderFile(file);
    }
  });
  bindReaderDropZone();

  els.reloadPromptLabBtn.addEventListener("click", loadPromptLabLibrary);
  els.generatePromptBtn.addEventListener("click", generatePrompt);
  els.useCurrentImageTagsBtn.addEventListener("click", useCurrentImageTags);

  els.similarUseSelectedBtn.addEventListener("click", async () => {
    switchView("similar");
    await loadSimilarForSelected();
  });
  els.similarFileInput.addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    if (file) {
      switchView("similar");
      loadSimilarForUpload(file);
    }
  });

  els.startManualSortBtn.addEventListener("click", startManualSort);
  els.clearManualSortBtn.addEventListener("click", clearManualSort);
  els.manualSkipBtn.addEventListener("click", () => manualSortAction("skip"));
  els.manualUndoBtn.addEventListener("click", () => manualSortAction("undo"));
  document.querySelectorAll(".action-btn").forEach((button) => {
    button.addEventListener("click", () => manualSortAction("move", button.dataset.sortKey));
  });

  els.themeToggleBtn.addEventListener("click", toggleTheme);

  document.addEventListener("keydown", async (event) => {
    if (isTypingElement(event.target)) {
      return;
    }
    if (state.view === "sorting" && state.manualSortActive) {
      const key = event.key.toLowerCase();
      if (["w", "a", "s", "d"].includes(key)) {
        event.preventDefault();
        await manualSortAction("move", key);
        return;
      }
      if (event.code === "Space") {
        event.preventDefault();
        await manualSortAction("skip");
        return;
      }
      if (key === "z") {
        event.preventDefault();
        await manualSortAction("undo");
      }
    }
  });

  [els.keyword, els.promptKeyword, els.filterTag, els.filterGenerator, els.filterCheckpoint, els.filterLora].forEach((input) => {
    input.addEventListener("keydown", async (event) => {
      if (event.key === "Enter") {
        state.page = 1;
        await loadImages();
      }
    });
  });
}

function cacheElements() {
  [
    "modelBadge",
    "scanDir",
    "scanRecursive",
    "scanMax",
    "scanBtn",
    "scanResult",
    "galleryStats",
    "keyword",
    "promptKeyword",
    "filterTag",
    "filterGenerator",
    "filterContentRating",
    "filterCheckpoint",
    "filterLora",
    "minRating",
    "maxRating",
    "minWidth",
    "maxWidth",
    "minHeight",
    "maxHeight",
    "aspectRatio",
    "sortBy",
    "applyFilterBtn",
    "resetFiltersBtn",
    "batchOnlyUntagged",
    "batchGeneralThreshold",
    "batchCharacterThreshold",
    "batchAutoTagBtn",
    "batchProgressFill",
    "batchProgressText",
    "batchMoveTargetDir",
    "batchMoveStrategy",
    "batchMoveBtn",
    "batchMoveStatus",
    "galleryList",
    "reloadBtn",
    "prevPage",
    "nextPage",
    "pageInfo",
    "resultSummary",
    "imageGrid",
    "detailHint",
    "detailStatus",
    "detailPreview",
    "detailName",
    "detailPath",
    "detailMeta",
    "detailModelMeta",
    "detailBadges",
    "detailCheckpoint",
    "detailLora",
    "detailPrompt",
    "detailNegative",
    "detailTagInput",
    "detailRatingInput",
    "saveRatingBtn",
    "saveTagsBtn",
    "autoTagsBtn",
    "openSimilarBtn",
    "detailTargetDir",
    "detailMoveStrategy",
    "moveBtn",
    "readerDropZone",
    "readerFileInput",
    "readerStatus",
    "readerPreview",
    "readerTitle",
    "readerInfo",
    "readerBadges",
    "readerPrompt",
    "readerNegative",
    "readerParams",
    "readerMetadata",
    "reloadPromptLabBtn",
    "promptQuality",
    "promptCountTag",
    "promptIncludeNegative",
    "promptRandomize",
    "promptSelectedTags",
    "useCurrentImageTagsBtn",
    "generatePromptBtn",
    "generatedPrompt",
    "generatedNegative",
    "promptLabStatus",
    "promptLabTags",
    "promptLabLibrary",
    "similarUseSelectedBtn",
    "similarFileInput",
    "similarStatus",
    "similarSourcePreview",
    "similarSourceInfo",
    "similarResultInfo",
    "similarGrid",
    "sortFolderW",
    "sortFolderA",
    "sortFolderS",
    "sortFolderD",
    "startManualSortBtn",
    "clearManualSortBtn",
    "manualSortStatus",
    "manualSortProgress",
    "manualUndoBtn",
    "manualSkipBtn",
    "manualSortPreview",
    "manualSortTitle",
    "manualSortInfo",
    "manualSortTags",
    "thumbTemplate",
    "themeToggleBtn",
  ].forEach((id) => {
    els[id] = byId(id);
  });
}

function toggleTheme() {
  const html = document.documentElement;
  const currentTheme = html.dataset.theme || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const newTheme = currentTheme === "dark" ? "light" : "dark";
  html.dataset.theme = newTheme;
  localStorage.setItem("sd-sorter-theme", newTheme);
}

async function init() {
  cacheElements();
  bindEvents();
  await Promise.all([updateModelRuntimeBadge(), loadLibraries(), loadPromptLabLibrary()]);
  await loadImages();
}

init();
