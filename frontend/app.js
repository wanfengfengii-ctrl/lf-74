const API_BASE = "/api";

let state = {
    leaves: [],
    plans: [],
    editingLeafId: null,
    editingPlanId: null,
    planSelectedAvailable: null,
    planSelectedSelected: null,
    planLeafOrder: [],
    currentViewingPlanId: null,
    annotate: {
        selectedLeafId: null,
        currentTool: "hole",
        image: null,
        canvas: null,
        ctx: null,
        holes: [],
        damage_regions: [],
        text_regions: [],
        scale: 1,
        imageWidth: 0,
        imageHeight: 0,
        drawing: false,
        drawStartX: 0,
        drawStartY: 0,
        pendingDamage: null,
        pendingText: null,
        selectedAnnotationId: null,
        highlightedId: null,
    },
    compare: {
        planA: null,
        planB: null,
        result: null,
    },
    audit: {
        logs: [],
        versions: [],
        selectedVersionPlanId: null,
        selectedVersionForCreate: null,
    },
};

function uid() {
    return "id_" + Math.random().toString(36).slice(2, 10);
}

async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: { "Content-Type": "application/json" },
            ...options,
        });
        const text = await response.text();
        let data = null;
        try {
            data = text ? JSON.parse(text) : null;
        } catch (e) {
            data = null;
        }
        if (!response.ok) {
            let errorMsg = `请求失败 (${response.status})`;
            if (data && data.detail) {
                errorMsg = data.detail;
            } else if (text && text.trim()) {
                try {
                    const parsed = JSON.parse(text);
                    if (parsed.detail) errorMsg = parsed.detail;
                    else errorMsg = text.substring(0, 200);
                } catch {
                    errorMsg = text.substring(0, 200);
                }
            }
            throw new Error(errorMsg);
        }
        return data;
    } catch (error) {
        showToast(error.message, "error");
        throw error;
    }
}

async function apiUpload(url, file) {
    const formData = new FormData();
    formData.append("file", file);
    try {
        const response = await fetch(url, {
            method: "POST",
            body: formData,
        });
        const text = await response.text();
        let data = null;
        try {
            data = text ? JSON.parse(text) : null;
        } catch (e) {
            data = null;
        }
        if (!response.ok) {
            let errorMsg = `请求失败 (${response.status})`;
            if (data && data.detail) errorMsg = data.detail;
            else if (text) errorMsg = text.substring(0, 200);
            throw new Error(errorMsg);
        }
        return data;
    } catch (error) {
        showToast(error.message, "error");
        throw error;
    }
}

function showToast(message, type = "success") {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => {
        toast.className = "toast";
    }, 3000);
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str ?? "";
    return div.innerHTML;
}

function openModal(id) {
    document.getElementById(id).classList.add("active");
}

function closeModal(id) {
    document.getElementById(id).classList.remove("active");
}

function initTabs() {
    const tabBtns = document.querySelectorAll(".tab-btn");
    tabBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            const tabId = btn.dataset.tab;
            tabBtns.forEach((b) => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
            btn.classList.add("active");
            document.getElementById(tabId).classList.add("active");
            if (tabId === "sort") populateStartLeafSelect();
            if (tabId === "annotate") populateAnnotateLeafSelect();
            if (tabId === "compare") populateCompareSelects();
            if (tabId === "audit") {
                populateVersionPlanSelect();
                loadAuditLogs();
            }
        });
    });
}

function initModals() {
    document.querySelectorAll(".close, [data-close]").forEach((el) => {
        el.addEventListener("click", () => {
            const modalId = el.dataset.modal || el.dataset.close;
            closeModal(modalId);
        });
    });

    document.querySelectorAll(".modal").forEach((modal) => {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) modal.classList.remove("active");
        });
    });
}

async function loadLeaves() {
    state.leaves = await apiRequest(`${API_BASE}/leaves`);
    renderLeaves();
}

function renderLeaves() {
    const container = document.getElementById("leavesList");
    if (state.leaves.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无叶片数据，点击右上角按钮添加</div>';
        return;
    }
    container.innerHTML = state.leaves
        .map(
            (leaf) => `
        <div class="leaf-card">
            <div class="leaf-card-header">
                <span class="leaf-id">${escapeHtml(leaf.id)}</span>
                ${leaf.confirmed
                    ? '<span class="leaf-confirmed-badge">已确认</span>'
                    : '<span class="leaf-unconfirmed-badge">未确认</span>'}
            </div>
            ${leaf.image_path ? `<img class="leaf-card-image" src="${API_BASE}/annotations/${leaf.id}/image" onerror="this.style.display='none'">` : ""}
            <div class="leaf-dims">尺寸：${leaf.length} × ${leaf.width} mm</div>
            <div class="leaf-holes">穿孔数：${leaf.holes.length}${leaf.holes.length > 0 ? " 个" : ""}</div>
            ${leaf.holes.length > 0 ? `<div class="leaf-holes">孔位：${leaf.holes.map((h) => `(${h.x}, ${h.y})`).join(", ")}</div>` : ""}
            ${leaf.residual_text ? `<div class="leaf-text-preview">${escapeHtml(leaf.residual_text)}</div>` : ""}
            ${leaf.damage ? `<div class="leaf-damage">⚠ ${escapeHtml(leaf.damage)}</div>` : ""}
            <div class="leaf-card-actions">
                <button class="btn btn-secondary" onclick="editLeaf('${leaf.id}')">编辑</button>
                <button class="btn btn-primary" onclick="gotoAnnotate('${leaf.id}')">标注</button>
                <button class="btn btn-danger" onclick="deleteLeaf('${leaf.id}')">删除</button>
            </div>
        </div>
    `
        )
        .join("");
}

function gotoAnnotate(leafId) {
    document.querySelectorAll(".tab-btn").forEach((b) => {
        b.classList.toggle("active", b.dataset.tab === "annotate");
    });
    document.querySelectorAll(".tab-content").forEach((c) => {
        c.classList.toggle("active", c.id === "annotate");
    });
    populateAnnotateLeafSelect();
    document.getElementById("annotateLeafSelect").value = leafId;
    loadLeafAnnotation(leafId);
}

async function openAddLeafModal() {
    state.editingLeafId = null;
    document.getElementById("leafModalTitle").textContent = "添加叶片";
    document.getElementById("leafForm").reset();
    document.getElementById("leafId").disabled = false;
    openModal("leafModal");
}

async function editLeaf(leafId) {
    const leaf = state.leaves.find((l) => l.id === leafId);
    if (!leaf) return;

    state.editingLeafId = leafId;
    document.getElementById("leafModalTitle").textContent = "编辑叶片";
    document.getElementById("leafId").value = leaf.id;
    document.getElementById("leafId").disabled = true;
    document.getElementById("leafLength").value = leaf.length;
    document.getElementById("leafWidth").value = leaf.width;
    document.getElementById("leafHoles").value = leaf.holes.map((h) => `${h.x}, ${h.y}`).join("\n");
    document.getElementById("leafText").value = leaf.residual_text || "";
    document.getElementById("leafDamage").value = leaf.damage || "";
    document.getElementById("leafConfirmed").checked = leaf.confirmed;
    openModal("leafModal");
}

async function submitLeafForm(e) {
    e.preventDefault();

    const holesText = document.getElementById("leafHoles").value.trim();
    const holes = [];
    const parseErrors = [];
    if (holesText) {
        const lines = holesText.split("\n").filter((l) => l.trim());
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            const parts = line.split(",").map((p) => p.trim());
            if (parts.length < 2) {
                parseErrors.push(`第 ${i + 1} 行格式错误：需要用逗号分隔两个数字`);
                continue;
            }
            const x = parseFloat(parts[0]);
            const y = parseFloat(parts[1]);
            if (isNaN(x) || isNaN(y)) {
                parseErrors.push(`第 ${i + 1} 行格式错误`);
                continue;
            }
            holes.push({ x, y });
        }
    }

    if (parseErrors.length > 0) {
        showToast("穿孔坐标格式错误", "error");
        return;
    }

    const leafLength = parseFloat(document.getElementById("leafLength").value);
    const leafWidth = parseFloat(document.getElementById("leafWidth").value);

    for (let i = 0; i < holes.length; i++) {
        const h = holes[i];
        if (h.x < 0 || h.x > leafWidth) parseErrors.push(`第 ${i + 1} 个穿孔 X 超出范围`);
        if (h.y < 0 || h.y > leafLength) parseErrors.push(`第 ${i + 1} 个穿孔 Y 超出范围`);
    }

    if (parseErrors.length > 0) {
        showToast("穿孔坐标超出范围", "error");
        return;
    }

    const payload = {
        length: leafLength,
        width: leafWidth,
        holes,
        residual_text: document.getElementById("leafText").value.trim(),
        damage: document.getElementById("leafDamage").value.trim(),
        confirmed: document.getElementById("leafConfirmed").checked,
    };

    if (state.editingLeafId) {
        await apiRequest(`${API_BASE}/leaves/${state.editingLeafId}`, {
            method: "PUT",
            body: JSON.stringify(payload),
        });
        showToast("叶片已更新");
    } else {
        payload.id = document.getElementById("leafId").value.trim();
        await apiRequest(`${API_BASE}/leaves`, {
            method: "POST",
            body: JSON.stringify(payload),
        });
        showToast("叶片已添加");
    }

    closeModal("leafModal");
    await loadLeaves();
    await loadPlans();
}

async function deleteLeaf(leafId) {
    if (!confirm(`确定要删除叶片 "${leafId}" 吗？`)) return;
    await apiRequest(`${API_BASE}/leaves/${leafId}`, { method: "DELETE" });
    showToast("叶片已删除");
    await loadLeaves();
    await loadPlans();
}

async function loadPlans() {
    state.plans = await apiRequest(`${API_BASE}/plans`);
    renderPlans();
}

function renderPlans() {
    const container = document.getElementById("plansList");
    if (state.plans.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无复原方案，点击右上角按钮新建</div>';
        return;
    }
    container.innerHTML = state.plans
        .map(
            (plan) => `
        <div class="plan-card" onclick="viewPlan('${plan.id}')">
            <div class="plan-card-header">
                <span class="plan-name">${escapeHtml(plan.name)}</span>
                ${plan.is_final ? '<span class="plan-final-badge">最终方案</span>' : ""}
            </div>
            <div class="plan-id">方案编号：${escapeHtml(plan.id)}</div>
            ${plan.description ? `<div class="plan-desc">${escapeHtml(plan.description)}</div>` : ""}
            <div class="plan-info">
                <span>叶片数量：${plan.leaves.length}</span>
                ${plan.score !== null && plan.score !== undefined ? `<span class="plan-score">评分：${plan.score}</span>` : ""}
            </div>
        </div>
    `
        )
        .join("");
}

async function openAddPlanModal() {
    state.editingPlanId = null;
    state.planLeafOrder = [];
    document.getElementById("planModalTitle").textContent = "新建复原方案";
    document.getElementById("planForm").reset();
    document.getElementById("planId").disabled = false;
    openModal("planModal");
    renderPlanLeafLists();
}

async function editPlan(planId) {
    const plan = state.plans.find((p) => p.id === planId);
    if (!plan) return;

    state.editingPlanId = planId;
    state.planLeafOrder = plan.leaves
        .slice()
        .sort((a, b) => a.order - b.order)
        .map((l) => l.leaf_id);

    document.getElementById("planModalTitle").textContent = "编辑复原方案";
    document.getElementById("planId").value = plan.id;
    document.getElementById("planId").disabled = true;
    document.getElementById("planName").value = plan.name;
    document.getElementById("planDescription").value = plan.description || "";
    document.getElementById("planFinal").checked = plan.is_final;
    closeModal("planDetailModal");
    openModal("planModal");
    renderPlanLeafLists();
}

function renderPlanLeafLists() {
    const available = document.getElementById("availableLeavesList");
    const selected = document.getElementById("selectedLeavesList");

    const selectedIds = new Set(state.planLeafOrder);
    const availableLeaves = state.leaves.filter((l) => !selectedIds.has(l.id));

    available.innerHTML =
        availableLeaves.length === 0
            ? '<div class="empty-state" style="padding:20px">无可用叶片</div>'
            : availableLeaves
                  .map(
                      (leaf) => `
            <div class="leaf-select-item ${state.planSelectedAvailable === leaf.id ? "selected" : ""}"
                 onclick="selectAvailableLeaf('${leaf.id}')">
                <strong>${escapeHtml(leaf.id)}</strong>
                ${leaf.confirmed ? "✓" : "○"}
                ${leaf.residual_text ? `<br><small>${escapeHtml(leaf.residual_text.substring(0, 30))}</small>` : ""}
            </div>
        `
                  )
                  .join("");

    selected.innerHTML =
        state.planLeafOrder.length === 0
            ? '<div class="empty-state" style="padding:20px">请选择叶片</div>'
            : state.planLeafOrder
                  .map((lid, idx) => {
                      const leaf = state.leaves.find((l) => l.id === lid);
                      if (!leaf) return "";
                      return `
                <div class="leaf-select-item ${state.planSelectedSelected === lid ? "selected" : ""}"
                     onclick="selectSelectedLeaf('${lid}')">
                    [${idx + 1}] <strong>${escapeHtml(leaf.id)}</strong>
                    ${leaf.confirmed ? "✓" : "○"}
                    ${leaf.residual_text ? `<br><small>${escapeHtml(leaf.residual_text.substring(0, 30))}</small>` : ""}
                </div>
            `;
                  })
                  .join("");
}

function selectAvailableLeaf(id) {
    state.planSelectedAvailable = state.planSelectedAvailable === id ? null : id;
    state.planSelectedSelected = null;
    renderPlanLeafLists();
}

function selectSelectedLeaf(id) {
    state.planSelectedSelected = state.planSelectedSelected === id ? null : id;
    state.planSelectedAvailable = null;
    renderPlanLeafLists();
}

function addLeafToPlan() {
    if (!state.planSelectedAvailable) return;
    state.planLeafOrder.push(state.planSelectedAvailable);
    state.planSelectedAvailable = null;
    renderPlanLeafLists();
}

function removeLeafFromPlan() {
    if (!state.planSelectedSelected) return;
    const idx = state.planLeafOrder.indexOf(state.planSelectedSelected);
    if (idx >= 0) state.planLeafOrder.splice(idx, 1);
    state.planSelectedSelected = null;
    renderPlanLeafLists();
}

function moveLeafUp() {
    if (!state.planSelectedSelected) return;
    const idx = state.planLeafOrder.indexOf(state.planSelectedSelected);
    if (idx > 0) {
        [state.planLeafOrder[idx - 1], state.planLeafOrder[idx]] = [
            state.planLeafOrder[idx],
            state.planLeafOrder[idx - 1],
        ];
        renderPlanLeafLists();
    }
}

function moveLeafDown() {
    if (!state.planSelectedSelected) return;
    const idx = state.planLeafOrder.indexOf(state.planSelectedSelected);
    if (idx < state.planLeafOrder.length - 1) {
        [state.planLeafOrder[idx + 1], state.planLeafOrder[idx]] = [
            state.planLeafOrder[idx],
            state.planLeafOrder[idx + 1],
        ];
        renderPlanLeafLists();
    }
}

async function submitPlanForm(e) {
    e.preventDefault();

    const leaves = state.planLeafOrder.map((lid, idx) => ({
        leaf_id: lid,
        order: idx,
        flipped: false,
        rotated: 0,
    }));

    const payload = {
        name: document.getElementById("planName").value.trim(),
        description: document.getElementById("planDescription").value.trim(),
        leaves,
        is_final: document.getElementById("planFinal").checked,
    };

    if (state.editingPlanId) {
        await apiRequest(`${API_BASE}/plans/${state.editingPlanId}`, {
            method: "PUT",
            body: JSON.stringify(payload),
        });
        showToast("方案已更新");
    } else {
        payload.id = document.getElementById("planId").value.trim();
        await apiRequest(`${API_BASE}/plans`, {
            method: "POST",
            body: JSON.stringify(payload),
        });
        showToast("方案已创建");
    }

    closeModal("planModal");
    await loadPlans();
}

async function viewPlan(planId) {
    const plan = state.plans.find((p) => p.id === planId);
    if (!plan) return;

    state.currentViewingPlanId = planId;
    document.getElementById("planDetailTitle").textContent = plan.name;

    const sortedLeaves = plan.leaves.slice().sort((a, b) => a.order - b.order);

    const leavesHtml =
        sortedLeaves.length === 0
            ? '<div class="empty-state">方案中暂无叶片</div>'
            : sortedLeaves
                  .map((pl) => {
                      const leaf = state.leaves.find((l) => l.id === pl.leaf_id);
                      if (!leaf) return "";
                      return `
                <div class="plan-detail-leaf">
                    <div class="plan-detail-leaf-order">${pl.order + 1}</div>
                    <div class="plan-detail-leaf-info">
                        <div class="plan-detail-leaf-id">${escapeHtml(leaf.id)}</div>
                        <div class="plan-detail-leaf-text">
                            尺寸 ${leaf.length}×${leaf.width}mm · 穿孔 ${leaf.holes.length}
                        </div>
                    </div>
                    <div class="plan-detail-leaf-info">
                        ${leaf.residual_text ? escapeHtml(leaf.residual_text.substring(0, 50)) : "（无残文）"}
                    </div>
                    <div class="plan-detail-leaf-flags">
                        ${leaf.confirmed ? '<span class="leaf-confirmed-badge">已确认</span>' : '<span class="leaf-unconfirmed-badge">未确认</span>'}
                    </div>
                </div>
            `;
                  })
                  .join("");

    const created = new Date(plan.created_at).toLocaleString("zh-CN");
    const updated = new Date(plan.updated_at).toLocaleString("zh-CN");

    document.getElementById("planDetailContent").innerHTML = `
        <div class="plan-detail-meta">
            <p><strong>方案编号：</strong>${escapeHtml(plan.id)}</p>
            ${plan.description ? `<p><strong>方案说明：</strong>${escapeHtml(plan.description)}</p>` : ""}
            <p><strong>状态：</strong>${plan.is_final ? "✅ 最终方案" : "📝 草稿方案"}</p>
            ${plan.score !== null && plan.score !== undefined ? `<p><strong>综合评分：</strong>${plan.score}</p>` : ""}
            <p><strong>创建时间：</strong>${created}</p>
            <p><strong>更新时间：</strong>${updated}</p>
        </div>
        <h3 style="margin: 16px 0 8px; color: #6b4423; font-size: 15px;">叶片排序</h3>
        <div class="plan-detail-leaves">${leavesHtml}</div>
    `;

    openModal("planDetailModal");
}

async function recalcPlanScore() {
    if (!state.currentViewingPlanId) return;
    await apiRequest(`${API_BASE}/plans/${state.currentViewingPlanId}/recalculate`, {
        method: "POST",
    });
    showToast("评分已重新计算");
    await loadPlans();
    await viewPlan(state.currentViewingPlanId);
}

async function deleteCurrentPlan() {
    if (!state.currentViewingPlanId) return;
    const plan = state.plans.find((p) => p.id === state.currentViewingPlanId);
    if (!plan) return;
    if (!confirm(`确定要删除方案 "${plan.name}" 吗？`)) return;
    await apiRequest(`${API_BASE}/plans/${state.currentViewingPlanId}`, { method: "DELETE" });
    showToast("方案已删除");
    closeModal("planDetailModal");
    await loadPlans();
}

function openCreateVersionFromDetail() {
    if (!state.currentViewingPlanId) return;
    state.audit.selectedVersionForCreate = state.currentViewingPlanId;
    document.getElementById("versionForm").reset();
    openModal("versionModal");
}

async function submitVersionForm(e) {
    e.preventDefault();
    const planId = state.audit.selectedVersionForCreate;
    if (!planId) return;

    const payload = {
        name: document.getElementById("versionName").value.trim(),
        description: document.getElementById("versionDesc").value.trim(),
    };

    await apiRequest(`${API_BASE}/audit/plans/${planId}/versions`, {
        method: "POST",
        body: JSON.stringify(payload),
    });
    showToast("版本快照已创建");
    closeModal("versionModal");
    state.audit.selectedVersionForCreate = null;
    if (state.audit.selectedVersionPlanId === planId) {
        loadPlanVersions(planId);
    }
}

function populateStartLeafSelect() {
    const select = document.getElementById("startLeafSelect");
    const currentValue = select.value;
    select.innerHTML = '<option value="">自动选择</option>';
    state.leaves.forEach((leaf) => {
        const opt = document.createElement("option");
        opt.value = leaf.id;
        opt.textContent = leaf.id;
        select.appendChild(opt);
    });
    if (currentValue && state.leaves.some((l) => l.id === currentValue)) {
        select.value = currentValue;
    }
}

function initSortControls() {
    document.getElementById("holeWeight").addEventListener("input", (e) => {
        document.getElementById("holeWeightVal").textContent = e.target.value;
    });
    document.getElementById("textWeight").addEventListener("input", (e) => {
        document.getElementById("textWeightVal").textContent = e.target.value;
    });
}

async function runSort() {
    const startId = document.getElementById("startLeafSelect").value;
    const holeWeight = parseFloat(document.getElementById("holeWeight").value);
    const textWeight = parseFloat(document.getElementById("textWeight").value);

    let url = `${API_BASE}/sort/all?hole_weight=${holeWeight}&text_weight=${textWeight}`;
    if (startId) url += `&start_leaf_id=${encodeURIComponent(startId)}`;

    const result = await apiRequest(url);
    renderSortResult(result);
}

function renderSortResult(result) {
    const container = document.getElementById("sortResult");
    if (!result || !result.ordered_leaves || result.ordered_leaves.length === 0) {
        container.innerHTML = '<div class="empty-state">无排序结果</div>';
        return;
    }

    const listHtml = result.ordered_leaves
        .map((item, idx) => {
            const leaf = state.leaves.find((l) => l.id === item.leaf_id);
            return `
        <div class="sort-item">
            <div class="sort-order">${idx + 1}</div>
            <div class="sort-item-info">
                <div class="sort-item-id">${escapeHtml(item.leaf_id)}</div>
                ${leaf && leaf.residual_text ? `<div style="font-size:12px; color:#8b7355; margin-top:2px;">${escapeHtml(leaf.residual_text.substring(0, 60))}</div>` : ""}
                <div class="sort-item-reason">${escapeHtml(item.reason)}</div>
            </div>
            <div class="sort-item-scores">
                <div class="score-row">
                    <span class="score-label">孔位分</span>
                    <span class="score-value">${item.hole_alignment_score.toFixed(3)}</span>
                </div>
                <div class="score-row">
                    <span class="score-label">残文分</span>
                    <span class="score-value">${item.text_continuity_score.toFixed(3)}</span>
                </div>
                <div class="score-row total-score-row">
                    <span class="score-label">总分</span>
                    <span class="score-value">${item.score.toFixed(3)}</span>
                </div>
            </div>
        </div>
    `;
        })
        .join("");

    container.innerHTML = `
        <div class="sort-result-header">
            <h3>推荐排序方案</h3>
            <span class="total-score">平均匹配度：${result.total_score}</span>
        </div>
        <div class="sort-list">${listHtml}</div>
    `;
}

function populateAnnotateLeafSelect() {
    const select = document.getElementById("annotateLeafSelect");
    const current = select.value;
    select.innerHTML = '<option value="">请先选择叶片</option>';
    state.leaves.forEach((l) => {
        const opt = document.createElement("option");
        opt.value = l.id;
        opt.textContent = `${l.id} (${l.length}×${l.width}mm)`;
        select.appendChild(opt);
    });
    if (current && state.leaves.some((l) => l.id === current)) {
        select.value = current;
    }
}

function initAnnotateTools() {
    document.querySelectorAll(".tool-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tool-btn").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            state.annotate.currentTool = btn.dataset.tool;
            updateCanvasCursor();
        });
    });

    document.getElementById("uploadImageBtn").addEventListener("click", () => {
        if (!state.annotate.selectedLeafId) {
            showToast("请先选择叶片", "error");
            return;
        }
        document.getElementById("imageFileInput").click();
    });

    document.getElementById("imageFileInput").addEventListener("change", handleImageUpload);
    document.getElementById("saveAnnotationBtn").addEventListener("click", saveAnnotation);

    document.getElementById("annotateLeafSelect").addEventListener("change", (e) => {
        const id = e.target.value;
        state.annotate.selectedLeafId = id || null;
        if (id) loadLeafAnnotation(id);
        else resetAnnotateState();
    });

    document.getElementById("realLength").addEventListener("change", updateScaleFromLength);
    document.getElementById("scaleValue").addEventListener("change", (e) => {
        state.annotate.scale = parseFloat(e.target.value) || 1;
        redrawCanvas();
    });

    const canvas = document.getElementById("annotateCanvas");
    canvas.addEventListener("click", handleCanvasClick);
    canvas.addEventListener("mousedown", handleCanvasMouseDown);
    canvas.addEventListener("mousemove", handleCanvasMouseMove);
    canvas.addEventListener("mouseup", handleCanvasMouseUp);
    canvas.addEventListener("mouseleave", handleCanvasMouseUp);

    document.getElementById("damageForm").addEventListener("submit", submitDamageForm);
    document.getElementById("textForm").addEventListener("submit", submitTextForm);
}

function updateCanvasCursor() {
    const canvas = document.getElementById("annotateCanvas");
    const tool = state.annotate.currentTool;
    canvas.style.cursor = tool === "hole" ? "crosshair" : "cell";
}

function resetAnnotateState() {
    state.annotate.image = null;
    state.annotate.holes = [];
    state.annotate.damage_regions = [];
    state.annotate.text_regions = [];
    state.annotate.scale = 1;
    state.annotate.imageWidth = 0;
    state.annotate.imageHeight = 0;
    state.annotate.highlightedId = null;
    document.getElementById("canvasPlaceholder").style.display = "block";
    document.getElementById("canvasPlaceholder").textContent = "请先选择叶片并上传高清图片";
    const canvas = document.getElementById("annotateCanvas");
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    canvas.width = 800;
    canvas.height = 500;
    renderAnnotationSidebar();
}

async function loadLeafAnnotation(leafId) {
    try {
        const annotation = await apiRequest(`${API_BASE}/annotations/${leafId}`);
        const leaf = state.leaves.find((l) => l.id === leafId);
        if (leaf) {
            document.getElementById("realLength").value = leaf.length;
        }

        if (annotation) {
            state.annotate.holes = annotation.holes || [];
            state.annotate.damage_regions = annotation.damage_regions || [];
            state.annotate.text_regions = annotation.text_regions || [];
            state.annotate.scale = annotation.scale || 1;
            state.annotate.imageWidth = annotation.image_width || 0;
            state.annotate.imageHeight = annotation.image_height || 0;
            document.getElementById("scaleValue").value = state.annotate.scale;
            if (annotation.image_path) {
                await loadImageToCanvas(`${API_BASE}/annotations/${leafId}/image`);
            } else {
                document.getElementById("canvasPlaceholder").style.display = "block";
                document.getElementById("canvasPlaceholder").textContent = "该叶片暂无图片，请点击上传图片";
                renderAnnotationSidebar();
            }
        } else {
            resetAnnotateState();
            document.getElementById("canvasPlaceholder").textContent = "该叶片暂无标注，请上传图片开始标注";
        }
    } catch (e) {
        console.error(e);
    }
}

async function handleImageUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    if (!state.annotate.selectedLeafId) {
        showToast("请先选择叶片", "error");
        return;
    }

    const result = await apiUpload(`${API_BASE}/annotations/${state.annotate.selectedLeafId}/upload-image`, file);
    showToast("图片上传成功");

    const reader = new FileReader();
    reader.onload = (ev) => {
        loadImageToCanvas(ev.target.result);
    };
    reader.readAsDataURL(file);

    e.target.value = "";
    await loadLeaves();
}

function loadImageToCanvas(src) {
    return new Promise((resolve) => {
        const img = new Image();
        img.onload = () => {
            state.annotate.image = img;
            state.annotate.imageWidth = img.width;
            state.annotate.imageHeight = img.height;
            const canvas = document.getElementById("annotateCanvas");
            canvas.width = img.width;
            canvas.height = img.height;
            document.getElementById("canvasPlaceholder").style.display = "none";
            updateScaleFromLength();
            redrawCanvas();
            renderAnnotationSidebar();
            resolve();
        };
        img.onerror = () => {
            document.getElementById("canvasPlaceholder").style.display = "block";
            document.getElementById("canvasPlaceholder").textContent = "图片加载失败";
            resolve();
        };
        img.src = src;
    });
}

function updateScaleFromLength() {
    const realLen = parseFloat(document.getElementById("realLength").value);
    if (realLen && state.annotate.imageHeight > 0) {
        const scale = state.annotate.imageHeight / realLen;
        state.annotate.scale = scale;
        document.getElementById("scaleValue").value = scale.toFixed(2);
    }
    redrawCanvas();
}

function getCanvasCoords(e) {
    const canvas = document.getElementById("annotateCanvas");
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY,
    };
}

function handleCanvasClick(e) {
    if (!state.annotate.image) return;
    if (state.annotate.currentTool !== "hole") return;
    if (state.annotate.drawing) return;

    const { x, y } = getCanvasCoords(e);
    const scale = state.annotate.scale;
    const hole = {
        id: uid(),
        x: x,
        y: y,
        real_x: scale > 0 ? x / scale : null,
        real_y: scale > 0 ? y / scale : null,
        note: "",
    };
    state.annotate.holes.push(hole);
    redrawCanvas();
    renderAnnotationSidebar();
}

function handleCanvasMouseDown(e) {
    if (!state.annotate.image) return;
    if (state.annotate.currentTool === "hole") return;

    const { x, y } = getCanvasCoords(e);
    state.annotate.drawing = true;
    state.annotate.drawStartX = x;
    state.annotate.drawStartY = y;
}

function handleCanvasMouseMove(e) {
    if (!state.annotate.drawing || !state.annotate.image) return;
    const { x, y } = getCanvasCoords(e);
    state.annotate.pendingDamage = {
        x: Math.min(state.annotate.drawStartX, x),
        y: Math.min(state.annotate.drawStartY, y),
        width: Math.abs(x - state.annotate.drawStartX),
        height: Math.abs(y - state.annotate.drawStartY),
    };
    redrawCanvas();
}

function handleCanvasMouseUp(e) {
    if (!state.annotate.drawing) return;
    state.annotate.drawing = false;

    const pending = state.annotate.pendingDamage;
    state.annotate.pendingDamage = null;

    if (!pending || pending.width < 5 || pending.height < 5) {
        redrawCanvas();
        return;
    }

    if (state.annotate.currentTool === "damage") {
        state.annotate.pendingDamage = {
            id: uid(),
            x: pending.x,
            y: pending.y,
            width: pending.width,
            height: pending.height,
            severity: "medium",
            description: "",
        };
        document.getElementById("damageSeverity").value = "medium";
        document.getElementById("damageDesc").value = "";
        openModal("damageModal");
    } else if (state.annotate.currentTool === "text") {
        state.annotate.pendingText = {
            id: uid(),
            x: pending.x,
            y: pending.y,
            width: pending.width,
            height: pending.height,
            text: "",
            linked_damage_ids: [],
        };
        document.getElementById("textContent").value = "";
        renderLinkedDamageList();
        openModal("textModal");
    }

    redrawCanvas();
}

function submitDamageForm(e) {
    e.preventDefault();
    const dmg = state.annotate.pendingDamage;
    if (!dmg) return closeModal("damageModal");
    dmg.severity = document.getElementById("damageSeverity").value;
    dmg.description = document.getElementById("damageDesc").value.trim();
    state.annotate.damage_regions.push(dmg);
    state.annotate.pendingDamage = null;
    closeModal("damageModal");
    redrawCanvas();
    renderAnnotationSidebar();
}

function renderLinkedDamageList() {
    const container = document.getElementById("linkedDamageList");
    if (state.annotate.damage_regions.length === 0) {
        container.innerHTML = '<span style="color:#8b7355; font-size:12px;">（暂无破损区域可关联）</span>';
        return;
    }
    container.innerHTML = state.annotate.damage_regions
        .map(
            (d, i) => `
        <label class="linked-damage-item">
            <input type="checkbox" value="${d.id}" data-damage-link>
            破损${i + 1} (${d.severity})
        </label>
    `
        )
        .join("");
}

function submitTextForm(e) {
    e.preventDefault();
    const txt = state.annotate.pendingText;
    if (!txt) return closeModal("textModal");
    txt.text = document.getElementById("textContent").value.trim();
    const linked = [];
    document.querySelectorAll("[data-damage-link]").forEach((cb) => {
        if (cb.checked) linked.push(cb.value);
    });
    txt.linked_damage_ids = linked;
    state.annotate.text_regions.push(txt);
    state.annotate.pendingText = null;
    closeModal("textModal");
    redrawCanvas();
    renderAnnotationSidebar();
}

function redrawCanvas() {
    const canvas = document.getElementById("annotateCanvas");
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (state.annotate.image) {
        ctx.drawImage(state.annotate.image, 0, 0);
    }

    ctx.save();

    state.annotate.damage_regions.forEach((d) => {
        const color = d.severity === "severe" ? "rgba(192,57,43,0.3)"
            : d.severity === "medium" ? "rgba(243,156,18,0.3)"
            : "rgba(241,196,15,0.3)";
        const border = d.severity === "severe" ? "#c0392b"
            : d.severity === "medium" ? "#f39c12"
            : "#f1c40f";
        ctx.fillStyle = color;
        ctx.strokeStyle = border;
        ctx.lineWidth = state.annotate.highlightedId === d.id ? 4 : 2;
        ctx.fillRect(d.x, d.y, d.width, d.height);
        ctx.strokeRect(d.x, d.y, d.width, d.height);
    });

    state.annotate.text_regions.forEach((t) => {
        ctx.fillStyle = "rgba(41,128,185,0.25)";
        ctx.strokeStyle = "#2980b9";
        ctx.lineWidth = state.annotate.highlightedId === t.id ? 4 : 2;
        ctx.fillRect(t.x, t.y, t.width, t.height);
        ctx.strokeRect(t.x, t.y, t.width, t.height);
        if (t.text) {
            ctx.fillStyle = "#fff";
            ctx.font = "bold 13px sans-serif";
            const label = t.text.substring(0, 10);
            ctx.fillText(label, t.x + 4, t.y + 16);
        }
    });

    state.annotate.holes.forEach((h, i) => {
        ctx.beginPath();
        ctx.arc(h.x, h.y, 10, 0, Math.PI * 2);
        ctx.fillStyle = state.annotate.highlightedId === h.id ? "#e74c3c" : "rgba(39,174,96,0.85)";
        ctx.fill();
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.fillStyle = "#fff";
        ctx.font = "bold 12px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(String(i + 1), h.x, h.y);
        ctx.textAlign = "start";
        ctx.textBaseline = "alphabetic";
    });

    if (state.annotate.pendingDamage) {
        const p = state.annotate.pendingDamage;
        ctx.strokeStyle = state.annotate.currentTool === "text" ? "#2980b9" : "#f39c12";
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.strokeRect(p.x, p.y, p.width, p.height);
        ctx.setLineDash([]);
    }

    ctx.restore();
}

function renderAnnotationSidebar() {
    document.getElementById("holeCount").textContent = state.annotate.holes.length;
    document.getElementById("damageCount").textContent = state.annotate.damage_regions.length;
    document.getElementById("textCount").textContent = state.annotate.text_regions.length;

    const hl = state.annotate.highlightedId;

    document.getElementById("holesList").innerHTML = state.annotate.holes.length === 0
        ? '<div style="font-size:12px; color:#8b7355;">（暂无）</div>'
        : state.annotate.holes
              .map(
                  (h, i) => `
        <div class="annotation-item ${hl === h.id ? "highlighted" : ""}" onclick="highlightAnnotation('${h.id}')">
            <span>孔${i + 1} (${h.x.toFixed(0)},${h.y.toFixed(0)})</span>
            <button class="annotation-item-delete" onclick="deleteHole('${h.id}')">×</button>
        </div>
    `
              )
              .join("");

    document.getElementById("damageList").innerHTML = state.annotate.damage_regions.length === 0
        ? '<div style="font-size:12px; color:#8b7355;">（暂无）</div>'
        : state.annotate.damage_regions
              .map(
                  (d, i) => `
        <div class="annotation-item ${hl === d.id ? "highlighted" : ""}" onclick="highlightAnnotation('${d.id}')">
            <span>破损${i + 1} [${d.severity}]</span>
            <button class="annotation-item-delete" onclick="deleteDamage('${d.id}')">×</button>
        </div>
    `
              )
              .join("");

    document.getElementById("textList").innerHTML = state.annotate.text_regions.length === 0
        ? '<div style="font-size:12px; color:#8b7355;">（暂无）</div>'
        : state.annotate.text_regions
              .map(
                  (t, i) => `
        <div class="annotation-item ${hl === t.id ? "highlighted" : ""}" onclick="highlightAnnotation('${t.id}')">
            <span>文字${i + 1}: ${escapeHtml(t.text.substring(0, 10)) || "(空)"}</span>
            <button class="annotation-item-delete" onclick="deleteText('${t.id}')">×</button>
        </div>
    `
              )
              .join("");
}

function highlightAnnotation(id) {
    state.annotate.highlightedId = state.annotate.highlightedId === id ? null : id;
    redrawCanvas();
    renderAnnotationSidebar();
}

function deleteHole(id) {
    state.annotate.holes = state.annotate.holes.filter((h) => h.id !== id);
    state.annotate.highlightedId = null;
    redrawCanvas();
    renderAnnotationSidebar();
}

function deleteDamage(id) {
    state.annotate.damage_regions = state.annotate.damage_regions.filter((d) => d.id !== id);
    state.annotate.text_regions.forEach((t) => {
        t.linked_damage_ids = t.linked_damage_ids.filter((lid) => lid !== id);
    });
    state.annotate.highlightedId = null;
    redrawCanvas();
    renderAnnotationSidebar();
}

function deleteText(id) {
    state.annotate.text_regions = state.annotate.text_regions.filter((t) => t.id !== id);
    state.annotate.highlightedId = null;
    redrawCanvas();
    renderAnnotationSidebar();
}

async function saveAnnotation() {
    const leafId = state.annotate.selectedLeafId;
    if (!leafId) {
        showToast("请先选择叶片", "error");
        return;
    }

    const payload = {
        scale: state.annotate.scale,
        image_width: state.annotate.imageWidth,
        image_height: state.annotate.imageHeight,
        holes: state.annotate.holes,
        damage_regions: state.annotate.damage_regions,
        text_regions: state.annotate.text_regions,
    };

    await apiRequest(`${API_BASE}/annotations/${leafId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
    });
    showToast("标注保存成功");
    await loadLeaves();
}

function populateCompareSelects() {
    ["comparePlanA", "comparePlanB"].forEach((id) => {
        const select = document.getElementById(id);
        const current = select.value;
        select.innerHTML = '<option value="">请选择方案</option>';
        state.plans.forEach((p) => {
            const opt = document.createElement("option");
            opt.value = p.id;
            opt.textContent = `${p.name} (${p.id})`;
            select.appendChild(opt);
        });
        if (current && state.plans.some((p) => p.id === current)) select.value = current;
    });
}

function initCompare() {
    document.getElementById("runCompareBtn").addEventListener("click", runCompare);
    document.getElementById("exportCompareBtn").addEventListener("click", exportCompareReport);
}

async function runCompare() {
    const a = document.getElementById("comparePlanA").value;
    const b = document.getElementById("comparePlanB").value;
    if (!a || !b) {
        showToast("请选择两个方案进行比对", "error");
        return;
    }
    if (a === b) {
        showToast("请选择两个不同的方案", "error");
        return;
    }

    const result = await apiRequest(`${API_BASE}/compare/plans?plan_a_id=${encodeURIComponent(a)}&plan_b_id=${encodeURIComponent(b)}`);
    state.compare.result = result;
    renderCompareResult(result);
    document.getElementById("exportCompareBtn").disabled = false;
}

function renderCompareResult(r) {
    const container = document.getElementById("compareResult");

    const diffA = r.score_diff !== null && r.score_diff !== undefined ? r.score_diff : 0;
    const diffText = diffA > 0 ? `B +${diffA.toFixed(3)}` : diffA < 0 ? `A ${diffA.toFixed(3)}` : "评分相同";
    const diffColor = diffA > 0 ? "#27ae60" : diffA < 0 ? "#c0392b" : "#8b7355";

    const diffItemsHtml = r.order_diffs
        .map((d) => {
            const tags = [];
            if (d.position_changed) tags.push('<span class="diff-change-tag pos">位置</span>');
            if (d.flipped_changed) tags.push('<span class="diff-change-tag flip">翻面</span>');
            if (d.is_disputed) tags.push('<span class="diff-change-tag disputed">⚠争议</span>');
            const posA = d.order_a !== null && d.order_a !== undefined ? d.order_a + 1 : "-";
            const posB = d.order_b !== null && d.order_b !== undefined ? d.order_b + 1 : "-";
            return `
                <div class="compare-diff-item ${d.is_disputed ? "disputed" : ""}">
                    <div style="font-weight:600; color:#6b4423;">${escapeHtml(d.leaf_id)}</div>
                    <div class="diff-position">
                        <span class="diff-order-box">A#${posA}</span>
                        <span class="diff-arrow">→</span>
                        <span class="diff-order-box">B#${posB}</span>
                    </div>
                    <div class="diff-changes">${tags.join("")}</div>
                    <div class="diff-reason">${escapeHtml(d.dispute_reason)}</div>
                </div>
            `;
        })
        .join("");

    container.innerHTML = `
        <div class="compare-header">
            <div class="compare-plan-card">
                <h4>方案 A</h4>
                <div class="score">${r.plan_a_score !== null && r.plan_a_score !== undefined ? r.plan_a_score.toFixed(3) : "-"}</div>
                <div class="meta">${escapeHtml(r.plan_a_name)} (${escapeHtml(r.plan_a_id)})</div>
            </div>
            <div class="compare-plan-card" style="text-align:center;">
                <h4>评分差异</h4>
                <div class="score" style="color:${diffColor}">${diffText}</div>
                <div class="meta">争议叶片 ${r.disputed_leaves.length} 片</div>
            </div>
            <div class="compare-plan-card">
                <h4>方案 B</h4>
                <div class="score">${r.plan_b_score !== null && r.plan_b_score !== undefined ? r.plan_b_score.toFixed(3) : "-"}</div>
                <div class="meta">${escapeHtml(r.plan_b_name)} (${escapeHtml(r.plan_b_id)})</div>
            </div>
        </div>
        <div class="compare-summary">
            <h4>叶片集合统计</h4>
            <div class="compare-summary-row">
                <span>共有叶片：${r.common_leaves.length} 片</span>
                <span>仅 A：${r.only_in_a.length} 片</span>
                <span>仅 B：${r.only_in_b.length} 片</span>
                <span class="badge-danger">争议叶片：${r.disputed_leaves.length} 片</span>
            </div>
            ${r.only_in_a.length ? `<div style="margin-top:8px; font-size:12px; color:#8b7355;">仅在A中: ${r.only_in_a.join(", ")}</div>` : ""}
            ${r.only_in_b.length ? `<div style="margin-top:4px; font-size:12px; color:#8b7355;">仅在B中: ${r.only_in_b.join(", ")}</div>` : ""}
        </div>
        <div class="diff-section-title">顺序差异详情</div>
        <div class="compare-diff-list">${diffItemsHtml || '<div class="empty-state-inline">两个方案完全一致</div>'}</div>
    `;
}

async function exportCompareReport() {
    const a = document.getElementById("comparePlanA").value;
    const b = document.getElementById("comparePlanB").value;
    if (!a || !b) return;
    const result = await apiRequest(`${API_BASE}/compare/plans/${encodeURIComponent(a)}/${encodeURIComponent(b)}/export?format=text`);
    downloadText(result.report, `comparison_${a}_vs_${b}.txt`);
}

function downloadText(text, filename) {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function populateVersionPlanSelect() {
    const select = document.getElementById("versionPlanSelect");
    const current = select.value;
    select.innerHTML = '<option value="">请选择方案</option>';
    state.plans.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `${p.name} (${p.id})`;
        select.appendChild(opt);
    });
    if (current && state.plans.some((p) => p.id === current)) select.value = current;
}

function initAudit() {
    document.getElementById("loadLogsBtn").addEventListener("click", loadAuditLogs);
    document.getElementById("loadVersionsBtn").addEventListener("click", () => {
        const pid = document.getElementById("versionPlanSelect").value;
        if (pid) loadPlanVersions(pid);
        else showToast("请先选择方案", "error");
    });
    document.getElementById("createVersionBtn").addEventListener("click", () => {
        const pid = document.getElementById("versionPlanSelect").value;
        if (!pid) {
            showToast("请先选择方案", "error");
            return;
        }
        state.audit.selectedVersionForCreate = pid;
        document.getElementById("versionForm").reset();
        openModal("versionModal");
    });
    document.getElementById("exportVersionsBtn").addEventListener("click", exportVersionsReport);
    document.getElementById("versionForm").addEventListener("submit", submitVersionForm);
}

async function loadAuditLogs() {
    const targetType = document.getElementById("logTargetType").value || null;
    const opType = document.getElementById("logOpType").value || null;
    let url = `${API_BASE}/audit/logs?limit=200`;
    if (targetType) url += `&target_type=${encodeURIComponent(targetType)}`;
    if (opType) url += `&operation_type=${encodeURIComponent(opType)}`;

    const logs = await apiRequest(url);
    state.audit.logs = logs;
    renderAuditLogs(logs);
}

function renderAuditLogs(logs) {
    const container = document.getElementById("auditLogs");
    if (!logs || logs.length === 0) {
        container.innerHTML = '<div class="empty-state-inline">暂无操作日志</div>';
        return;
    }

    const opLabels = {
        create: "创建",
        update: "更新",
        delete: "删除",
        upload: "上传",
        restore: "恢复",
        confirm: "确认",
        snapshot: "快照",
    };
    const targetLabels = { leaf: "叶片", plan: "方案", annotation: "标注" };

    container.innerHTML = logs
        .map((log) => {
            const time = new Date(log.created_at).toLocaleString("zh-CN");
            const opLabel = opLabels[log.operation_type] || log.operation_type;
            const targetLabel = targetLabels[log.target_type] || log.target_type;
            return `
                <div class="timeline-item ${log.operation_type}">
                    <div class="timeline-header">
                        <span class="timeline-type ${log.operation_type}">${opLabel}</span>
                        <span class="timeline-time">${time}</span>
                    </div>
                    <div class="timeline-desc">${escapeHtml(log.description)}</div>
                    <div class="timeline-target">${targetLabel} #${escapeHtml(log.target_id)} · ${escapeHtml(log.operator)}</div>
                </div>
            `;
        })
        .join("");
}

async function loadPlanVersions(planId) {
    state.audit.selectedVersionPlanId = planId;
    const versions = await apiRequest(`${API_BASE}/audit/plans/${encodeURIComponent(planId)}/versions`);
    state.audit.versions = versions;
    renderPlanVersions(versions);
    document.getElementById("exportVersionsBtn").disabled = versions.length === 0;
}

function renderPlanVersions(versions) {
    const container = document.getElementById("planVersions");
    if (!versions || versions.length === 0) {
        container.innerHTML = '<div class="empty-state-inline">暂无版本快照，点击"创建快照"保存当前方案状态</div>';
        return;
    }

    container.innerHTML = versions
        .map((v) => {
            const time = new Date(v.created_at).toLocaleString("zh-CN");
            return `
                <div class="version-card">
                    <div class="version-tag">v${v.version}</div>
                    <div class="version-info">
                        <h5>${escapeHtml(v.name || `版本 ${v.version}`)}</h5>
                        ${v.description ? `<p>${escapeHtml(v.description)}</p>` : ""}
                        <p>叶片 ${v.leaves?.length || 0} 片${v.score !== null && v.score !== undefined ? ` · 评分 ${v.score}` : ""}${v.is_final ? " · 最终方案" : ""}</p>
                        <p>${time} · ${escapeHtml(v.operator)}</p>
                    </div>
                    <div class="version-actions">
                        <button class="btn btn-secondary" onclick="restoreVersion('${v.id}')">恢复到此</button>
                        <button class="btn btn-danger" onclick="deleteVersion('${v.id}')">删除</button>
                    </div>
                </div>
            `;
        })
        .join("");
}

async function restoreVersion(versionId) {
    if (!confirm("确定要将方案恢复到此版本吗？当前未保存的修改将丢失。")) return;
    const result = await apiRequest(`${API_BASE}/audit/versions/${encodeURIComponent(versionId)}/restore`, {
        method: "POST",
    });
    showToast("方案已恢复");
    await loadPlans();
    const pid = state.audit.selectedVersionPlanId;
    if (pid) loadPlanVersions(pid);
}

async function deleteVersion(versionId) {
    if (!confirm("确定要删除此版本快照吗？")) return;
    await apiRequest(`${API_BASE}/audit/versions/${encodeURIComponent(versionId)}`, { method: "DELETE" });
    showToast("版本已删除");
    const pid = state.audit.selectedVersionPlanId;
    if (pid) loadPlanVersions(pid);
}

async function exportVersionsReport() {
    const pid = state.audit.selectedVersionPlanId;
    if (!pid) return;
    const result = await apiRequest(`${API_BASE}/audit/plans/${encodeURIComponent(pid)}/export`);
    downloadText(result.report, `plan_versions_${pid}.txt`);
}

async function init() {
    initTabs();
    initModals();
    initSortControls();
    initAnnotateTools();
    initCompare();
    initAudit();

    document.getElementById("addLeafBtn").addEventListener("click", openAddLeafModal);
    document.getElementById("leafForm").addEventListener("submit", submitLeafForm);
    document.getElementById("addPlanBtn").addEventListener("click", openAddPlanModal);
    document.getElementById("planForm").addEventListener("submit", submitPlanForm);
    document.getElementById("runSortBtn").addEventListener("click", runSort);
    document.getElementById("addLeafToPlan").addEventListener("click", addLeafToPlan);
    document.getElementById("removeLeafFromPlan").addEventListener("click", removeLeafFromPlan);
    document.getElementById("moveLeafUp").addEventListener("click", moveLeafUp);
    document.getElementById("moveLeafDown").addEventListener("click", moveLeafDown);
    document.getElementById("editPlanBtn").addEventListener("click", () => {
        if (state.currentViewingPlanId) editPlan(state.currentViewingPlanId);
    });
    document.getElementById("deletePlanBtn").addEventListener("click", deleteCurrentPlan);
    document.getElementById("recalcScoreBtn").addEventListener("click", recalcPlanScore);
    document.getElementById("createSnapshotBtn").addEventListener("click", openCreateVersionFromDetail);

    try {
        await loadLeaves();
        await loadPlans();
    } catch (e) {
        console.error("加载数据失败:", e);
    }
}

document.addEventListener("DOMContentLoaded", init);
