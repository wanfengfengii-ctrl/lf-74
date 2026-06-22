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
    collaboration: {
        researchers: [],
        projects: [],
        submissions: [],
        editingResearcherId: null,
        currentProjectId: null,
        currentProject: null,
        submissionLeafOrder: [],
        submissionLeafFlipped: {},
        submissionAvailableSel: null,
        submissionSelectedSel: null,
        opinions: [],
        disputes: [],
        discussions: [],
        consensusVersions: [],
        summary: null,
        currentDetailProjectId: null,
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

function initCollabSubtabs() {
    document.querySelectorAll(".collab-tab-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const tabId = btn.dataset.collabTab;
            document.querySelectorAll(".collab-tab-btn").forEach((b) => b.classList.remove("active"));
            document.querySelectorAll(".collab-tab-content").forEach((c) => c.classList.remove("active"));
            btn.classList.add("active");
            document.getElementById(`collab-${tabId}`).classList.add("active");
            if (tabId === "researchers") loadResearchers();
            if (tabId === "projects") loadCollabProjects();
            if (tabId === "submission") {
                populateSubmissionProjectSelect();
                populateSubmissionResearcherSelect();
            }
            if (tabId === "summary") populateSummaryProjectSelect();
            if (tabId === "discussions") {
                populateDiscussionProjectSelect();
                populateDiscussionResearcherSelect();
            }
            if (tabId === "consensus") populateConsensusProjectSelect();
        });
    });
}

async function loadResearchers() {
    state.collaboration.researchers = await apiRequest(`${API_BASE}/collaboration/researchers`);
    renderResearchers();
}

function renderResearchers() {
    const container = document.getElementById("researchersList");
    if (state.collaboration.researchers.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无研究者，点击右上角按钮添加</div>';
        return;
    }
    container.innerHTML = state.collaboration.researchers
        .map(
            (r) => `
        <div class="researcher-card">
            <div class="researcher-card-header">
                <span class="researcher-name">${escapeHtml(r.name)}</span>
                <span class="researcher-id">#${escapeHtml(r.id)}</span>
            </div>
            ${r.affiliation ? `<div class="researcher-affiliation">🏛 ${escapeHtml(r.affiliation)}</div>` : ""}
            ${r.email ? `<div class="researcher-email">✉ ${escapeHtml(r.email)}</div>` : ""}
            ${r.expertise ? `<div class="researcher-expertise">🔬 ${escapeHtml(r.expertise)}</div>` : ""}
            <div class="researcher-card-actions">
                <button class="btn btn-secondary" onclick="editResearcher('${r.id}')">编辑</button>
                <button class="btn btn-danger" onclick="deleteResearcher('${r.id}')">删除</button>
            </div>
        </div>
    `
        )
        .join("");
}

function openAddResearcherModal() {
    state.collaboration.editingResearcherId = null;
    document.getElementById("researcherModalTitle").textContent = "添加研究者";
    document.getElementById("researcherForm").reset();
    document.getElementById("researcherId").disabled = false;
    openModal("researcherModal");
}

function editResearcher(researcherId) {
    const r = state.collaboration.researchers.find((x) => x.id === researcherId);
    if (!r) return;
    state.collaboration.editingResearcherId = researcherId;
    document.getElementById("researcherModalTitle").textContent = "编辑研究者";
    document.getElementById("researcherId").value = r.id;
    document.getElementById("researcherId").disabled = true;
    document.getElementById("researcherName").value = r.name;
    document.getElementById("researcherAffiliation").value = r.affiliation || "";
    document.getElementById("researcherEmail").value = r.email || "";
    document.getElementById("researcherExpertise").value = r.expertise || "";
    openModal("researcherModal");
}

async function submitResearcherForm(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById("researcherName").value.trim(),
        affiliation: document.getElementById("researcherAffiliation").value.trim(),
        email: document.getElementById("researcherEmail").value.trim(),
        expertise: document.getElementById("researcherExpertise").value.trim(),
    };
    if (state.collaboration.editingResearcherId) {
        await apiRequest(`${API_BASE}/collaboration/researchers/${state.collaboration.editingResearcherId}`, {
            method: "PUT",
            body: JSON.stringify(payload),
        });
        showToast("研究者信息已更新");
    } else {
        payload.id = document.getElementById("researcherId").value.trim();
        await apiRequest(`${API_BASE}/collaboration/researchers`, {
            method: "POST",
            body: JSON.stringify(payload),
        });
        showToast("研究者已添加");
    }
    closeModal("researcherModal");
    await loadResearchers();
}

async function deleteResearcher(researcherId) {
    if (!confirm(`确定要删除研究者 "${researcherId}" 吗？`)) return;
    await apiRequest(`${API_BASE}/collaboration/researchers/${researcherId}`, { method: "DELETE" });
    showToast("研究者已删除");
    await loadResearchers();
}

async function loadCollabProjects() {
    state.collaboration.projects = await apiRequest(`${API_BASE}/collaboration/projects`);
    renderCollabProjects();
}

function renderCollabProjects() {
    const container = document.getElementById("projectsList");
    if (state.collaboration.projects.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无协同项目，点击右上角按钮新建</div>';
        return;
    }
    const statusLabels = {
        ongoing: "进行中",
        discussing: "讨论中",
        finalized: "已完成",
    };
    container.innerHTML = state.collaboration.projects
        .map(
            (p) => `
        <div class="project-card" onclick="viewProjectDetail('${p.id}')">
            <div class="project-card-header">
                <span class="project-name">${escapeHtml(p.name)}</span>
                <span class="project-status status-${p.status}">${statusLabels[p.status] || p.status}</span>
            </div>
            <div class="project-id">项目编号：${escapeHtml(p.id)}</div>
            ${p.description ? `<div class="project-desc">${escapeHtml(p.description)}</div>` : ""}
            <div class="project-meta">
                <span>目标叶片 ${p.target_leaf_ids.length} 片</span>
                <span>研究者 ${p.researcher_ids.length} 人</span>
            </div>
        </div>
    `
        )
        .join("");
}

async function openAddProjectModal() {
    state.collaboration.editingResearcherId = null;
    document.getElementById("projectModalTitle").textContent = "新建协同项目";
    document.getElementById("projectForm").reset();
    document.getElementById("projectId").disabled = false;
    renderProjectMultiSelects();
    openModal("projectModal");
}

function renderProjectMultiSelects() {
    const leafContainer = document.getElementById("projectLeafList");
    leafContainer.innerHTML =
        state.leaves.length === 0
            ? '<div class="empty-state-inline">暂无叶片</div>'
            : state.leaves
                  .map(
                      (l) => `
        <label class="multi-select-item">
            <input type="checkbox" value="${l.id}" data-project-leaf>
            <strong>${escapeHtml(l.id)}</strong>
            <small>${l.length}×${l.width}mm · ${l.holes.length}孔</small>
        </label>
    `
                  )
                  .join("");

    const researcherContainer = document.getElementById("projectResearcherList");
    researcherContainer.innerHTML =
        state.collaboration.researchers.length === 0
            ? '<div class="empty-state-inline">暂无研究者，请先添加</div>'
            : state.collaboration.researchers
                  .map(
                      (r) => `
        <label class="multi-select-item">
            <input type="checkbox" value="${r.id}" data-project-researcher>
            <strong>${escapeHtml(r.name)}</strong>
            <small>#${escapeHtml(r.id)}${r.affiliation ? ` · ${escapeHtml(r.affiliation)}` : ""}</small>
        </label>
    `
                  )
                  .join("");
}

async function submitProjectForm(e) {
    e.preventDefault();
    const target_leaf_ids = [];
    document.querySelectorAll("[data-project-leaf]").forEach((cb) => {
        if (cb.checked) target_leaf_ids.push(cb.value);
    });
    const researcher_ids = [];
    document.querySelectorAll("[data-project-researcher]").forEach((cb) => {
        if (cb.checked) researcher_ids.push(cb.value);
    });
    if (target_leaf_ids.length === 0) {
        showToast("请至少选择一片目标叶片", "error");
        return;
    }
    if (researcher_ids.length === 0) {
        showToast("请至少选择一位参与研究者", "error");
        return;
    }
    const payload = {
        name: document.getElementById("projectName").value.trim(),
        description: document.getElementById("projectDescription").value.trim(),
        target_leaf_ids,
        researcher_ids,
        created_by: document.getElementById("projectCreatedBy").value.trim() || "system",
    };
    payload.id = document.getElementById("projectId").value.trim();
    await apiRequest(`${API_BASE}/collaboration/projects`, {
        method: "POST",
        body: JSON.stringify(payload),
    });
    showToast("协同项目已创建");
    closeModal("projectModal");
    await loadCollabProjects();
}

async function viewProjectDetail(projectId) {
    const p = state.collaboration.projects.find((x) => x.id === projectId);
    if (!p) return;
    state.collaboration.currentDetailProjectId = projectId;
    document.getElementById("projectDetailTitle").textContent = p.name;

    const statusLabels = { ongoing: "🔄 进行中", discussing: "💬 讨论中", finalized: "✅ 已完成" };
    const researchers = state.collaboration.researchers.filter((r) => p.researcher_ids.includes(r.id));
    const leaves = state.leaves.filter((l) => p.target_leaf_ids.includes(l.id));

    document.getElementById("projectDetailContent").innerHTML = `
        <div class="project-detail-meta">
            <p><strong>项目编号：</strong>${escapeHtml(p.id)}</p>
            ${p.description ? `<p><strong>项目说明：</strong>${escapeHtml(p.description)}</p>` : ""}
            <p><strong>状态：</strong>${statusLabels[p.status] || p.status}</p>
            <p><strong>创建时间：</strong>${new Date(p.created_at).toLocaleString("zh-CN")}</p>
            <p><strong>更新时间：</strong>${new Date(p.updated_at).toLocaleString("zh-CN")}</p>
        </div>
        <h4 style="margin:16px 0 8px; color:#6b4423;">参与研究者（${researchers.length}人）</h4>
        <div class="project-detail-list">
            ${researchers
                .map((r) => `<div class="project-detail-chip">${escapeHtml(r.name)}<small>· #${escapeHtml(r.id)}</small></div>`)
                .join("") || '<span class="empty-state-inline">暂无</span>'}
        </div>
        <h4 style="margin:16px 0 8px; color:#6b4423;">目标叶片（${leaves.length}片）</h4>
        <div class="project-detail-list">
            ${leaves
                .map((l) => `<div class="project-detail-chip">${escapeHtml(l.id)}<small>· ${l.length}×${l.width}mm</small></div>`)
                .join("") || '<span class="empty-state-inline">暂无</span>'}
        </div>
    `;
    openModal("projectDetailModal");
}

async function deleteCurrentProject() {
    const pid = state.collaboration.currentDetailProjectId;
    if (!pid) return;
    if (!confirm("确定要删除该协同项目吗？")) return;
    await apiRequest(`${API_BASE}/collaboration/projects/${pid}`, { method: "DELETE" });
    showToast("项目已删除");
    closeModal("projectDetailModal");
    await loadCollabProjects();
}

async function viewCurrentProjectSubmissions() {
    const pid = state.collaboration.currentDetailProjectId;
    if (!pid) return;
    document.querySelectorAll(".collab-tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".collab-tab-content").forEach((c) => c.classList.remove("active"));
    document.querySelector('.collab-tab-btn[data-collab-tab="submission"]').classList.add("active");
    document.getElementById("collab-submission").classList.add("active");
    closeModal("projectDetailModal");
    populateSubmissionProjectSelect();
    populateSubmissionResearcherSelect();
    document.getElementById("submissionProjectSelect").value = pid;
    await loadExistingSubmissions(pid);
}

async function loadExistingSubmissions(pid) {
    if (!pid) {
        document.getElementById("existingSubmissionsList").innerHTML = '<div class="empty-state-inline">请先选择协同项目</div>';
        return;
    }
    try {
        const resp = await fetch(`/api/collaboration/projects/${encodeURIComponent(pid)}/submissions`);
        if (!resp.ok) throw new Error(await resp.text());
        const subs = await resp.json();
        state.collaboration.submissions = subs;
        renderExistingSubmissions();
    } catch (e) {
        showToast("加载提交记录失败：" + e.message, "error");
        document.getElementById("existingSubmissionsList").innerHTML = '<div class="empty-state-inline">加载失败</div>';
    }
}

function renderExistingSubmissions() {
    const box = document.getElementById("existingSubmissionsList");
    const subs = state.collaboration.submissions || [];
    if (subs.length === 0) {
        box.innerHTML = '<div class="empty-state-inline">该项目暂无提交记录</div>';
        return;
    }
    box.innerHTML = subs.map((s) => {
        const orderChips = (s.ordered_leaves || [])
            .slice()
            .sort((a, b) => (a.order || 0) - (b.order || 0))
            .map((rl) => {
                const flip = rl.is_flipped || rl.flipped ? " (翻面)" : "";
                return `<span class="submission-order-chip">#${rl.order || 0} ${rl.leaf_id}${flip}</span>`;
            })
            .join("");
        const finalTag = s.is_final
            ? '<span class="submission-final-tag">最终提交</span>'
            : '<span class="submission-final-tag draft">草稿</span>';
        const submittedAt = new Date(s.submitted_at).toLocaleString();
        const opinionCount = (s.annotation_opinions || []).length;
        const disputeCount = (s.dispute_notes || []).length;
        const remarksHtml = s.remarks
            ? `<div class="submission-remarks">整体备注：${escapeHtml(s.remarks)}</div>`
            : "";
        return `
            <div class="submission-card">
                <div class="submission-card-header">
                    <span class="submission-researcher">${escapeHtml(s.researcher_name || s.researcher_id)}</span>
                    ${finalTag}
                </div>
                <div class="submission-meta">提交时间：${submittedAt}</div>
                <div class="submission-meta">排序结果（${s.ordered_leaves?.length || 0}片）：</div>
                <div class="submission-order-list">${orderChips || '<span style="color:#8b7355;font-size:13px;">未排序</span>'}</div>
                <div class="submission-stats-row">
                    <span>📝 标注意见：${opinionCount}条</span>
                    <span>⚠️ 争议说明：${disputeCount}条</span>
                </div>
                ${remarksHtml}
            </div>
        `;
    }).join("");
}

function populateSubmissionProjectSelect() {
    const select = document.getElementById("submissionProjectSelect");
    const current = select.value;
    select.innerHTML = '<option value="">请先选择协同项目</option>';
    state.collaboration.projects.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `${p.name} (${p.target_leaf_ids.length}片·${p.researcher_ids.length}人)`;
        select.appendChild(opt);
    });
    if (current && state.collaboration.projects.some((p) => p.id === current)) select.value = current;
}

function populateSubmissionResearcherSelect() {
    const select = document.getElementById("submissionResearcherSelect");
    const current = select.value;
    select.innerHTML = '<option value="">请先选择研究者</option>';
    state.collaboration.researchers.forEach((r) => {
        const opt = document.createElement("option");
        opt.value = r.id;
        opt.textContent = `${r.name} (#${r.id})`;
        select.appendChild(opt);
    });
    if (current && state.collaboration.researchers.some((r) => r.id === current)) select.value = current;
}

async function loadSubmissionProject() {
    const pid = document.getElementById("submissionProjectSelect").value;
    const rid = document.getElementById("submissionResearcherSelect").value;
    if (!pid) {
        showToast("请选择协同项目", "error");
        return;
    }
    if (!rid) {
        showToast("请选择研究者", "error");
        return;
    }
    const project = state.collaboration.projects.find((p) => p.id === pid);
    if (!project) return;
    if (!project.researcher_ids.includes(rid)) {
        showToast("该研究者未参与此项目", "error");
        return;
    }
    state.collaboration.currentProjectId = pid;
    state.collaboration.currentProject = project;
    state.collaboration.submissionLeafOrder = [];
    state.collaboration.submissionLeafFlipped = {};
    state.collaboration.submissionAvailableSel = null;
    state.collaboration.submissionSelectedSel = null;
    state.collaboration.opinions = [];
    state.collaboration.disputes = [];
    document.getElementById("submissionArea").style.display = "block";
    renderSubmissionLeafLists();
    populateSubmissionLeafSelects();
    renderOpinionsList();
    renderDisputesList();
    document.getElementById("submissionRemarks").value = "";
    document.getElementById("submissionFinal").checked = false;
    await loadExistingSubmissions(pid);
}

function renderSubmissionLeafLists() {
    const project = state.collaboration.currentProject;
    if (!project) return;
    const targetSet = new Set(project.target_leaf_ids);
    const availableContainer = document.getElementById("submissionAvailableLeaves");
    const selectedContainer = document.getElementById("submissionSelectedLeaves");

    const selectedIds = new Set(state.collaboration.submissionLeafOrder);
    const available = state.leaves.filter((l) => targetSet.has(l.id) && !selectedIds.has(l.id));

    availableContainer.innerHTML =
        available.length === 0
            ? '<div class="empty-state" style="padding:15px;">无待排叶片</div>'
            : available
                  .map(
                      (l) => `
        <div class="leaf-select-item ${state.collaboration.submissionAvailableSel === l.id ? "selected" : ""}"
             onclick="selectSubmissionAvailable('${l.id}')">
            <strong>${escapeHtml(l.id)}</strong>
            ${l.residual_text ? `<br><small>${escapeHtml(l.residual_text.substring(0, 25))}</small>` : ""}
        </div>
    `
                  )
                  .join("");

    selectedContainer.innerHTML =
        state.collaboration.submissionLeafOrder.length === 0
            ? '<div class="empty-state" style="padding:15px;">请从左侧选择叶片</div>'
            : state.collaboration.submissionLeafOrder
                  .map((lid, idx) => {
                      const l = state.leaves.find((x) => x.id === lid);
                      if (!l) return "";
                      const flipped = !!state.collaboration.submissionLeafFlipped[lid];
                      return `
        <div class="leaf-select-item ${state.collaboration.submissionSelectedSel === lid ? "selected" : ""}"
             onclick="selectSubmissionSelected('${lid}')">
            <div>[${idx + 1}] <strong>${escapeHtml(lid)}</strong></div>
            ${l.residual_text ? `<small>${escapeHtml(l.residual_text.substring(0, 25))}</small>` : ""}
            <div class="submission-flip-control">
                <label>
                    <input type="checkbox" ${flipped ? "checked" : ""} onclick="event.stopPropagation(); toggleSubmissionFlip('${lid}', this.checked)">
                    翻面
                </label>
            </div>
        </div>
    `;
                  })
                  .join("");
}

function selectSubmissionAvailable(id) {
    state.collaboration.submissionAvailableSel =
        state.collaboration.submissionAvailableSel === id ? null : id;
    state.collaboration.submissionSelectedSel = null;
    renderSubmissionLeafLists();
}

function selectSubmissionSelected(id) {
    state.collaboration.submissionSelectedSel =
        state.collaboration.submissionSelectedSel === id ? null : id;
    state.collaboration.submissionAvailableSel = null;
    renderSubmissionLeafLists();
}

function toggleSubmissionFlip(lid, checked) {
    state.collaboration.submissionLeafFlipped[lid] = checked;
}

function addLeafToSubmission() {
    if (!state.collaboration.submissionAvailableSel) return;
    state.collaboration.submissionLeafOrder.push(state.collaboration.submissionAvailableSel);
    state.collaboration.submissionAvailableSel = null;
    renderSubmissionLeafLists();
}

function removeLeafFromSubmission() {
    if (!state.collaboration.submissionSelectedSel) return;
    const idx = state.collaboration.submissionLeafOrder.indexOf(state.collaboration.submissionSelectedSel);
    if (idx >= 0) state.collaboration.submissionLeafOrder.splice(idx, 1);
    delete state.collaboration.submissionLeafFlipped[state.collaboration.submissionSelectedSel];
    state.collaboration.submissionSelectedSel = null;
    renderSubmissionLeafLists();
}

function submissionLeafMoveUp() {
    if (!state.collaboration.submissionSelectedSel) return;
    const idx = state.collaboration.submissionLeafOrder.indexOf(state.collaboration.submissionSelectedSel);
    if (idx > 0) {
        [state.collaboration.submissionLeafOrder[idx - 1], state.collaboration.submissionLeafOrder[idx]] = [
            state.collaboration.submissionLeafOrder[idx],
            state.collaboration.submissionLeafOrder[idx - 1],
        ];
        renderSubmissionLeafLists();
    }
}

function submissionLeafMoveDown() {
    if (!state.collaboration.submissionSelectedSel) return;
    const idx = state.collaboration.submissionLeafOrder.indexOf(state.collaboration.submissionSelectedSel);
    if (idx < state.collaboration.submissionLeafOrder.length - 1) {
        [state.collaboration.submissionLeafOrder[idx + 1], state.collaboration.submissionLeafOrder[idx]] = [
            state.collaboration.submissionLeafOrder[idx],
            state.collaboration.submissionLeafOrder[idx + 1],
        ];
        renderSubmissionLeafLists();
    }
}

function populateSubmissionLeafSelects() {
    const project = state.collaboration.currentProject;
    if (!project) return;
    ["opinionLeafSelect", "disputeLeafSelect", "discussionLeafSelect"].forEach((id) => {
        const select = document.getElementById(id);
        if (!select) return;
        select.innerHTML = id === "discussionLeafSelect" ? '<option value="">（可选）</option>' : '<option value="">选择叶片</option>';
        project.target_leaf_ids.forEach((lid) => {
            const opt = document.createElement("option");
            opt.value = lid;
            opt.textContent = lid;
            select.appendChild(opt);
        });
    });
}

function initSubmissionControls() {
    document.getElementById("opinionConfidence").addEventListener("input", (e) => {
        document.getElementById("opinionConfidenceVal").textContent = e.target.value;
    });
}

function addOpinion() {
    const leaf_id = document.getElementById("opinionLeafSelect").value;
    const opinion_type = document.getElementById("opinionTypeSelect").value;
    const content = document.getElementById("opinionContent").value.trim();
    const confidence = parseFloat(document.getElementById("opinionConfidence").value);
    const reference = document.getElementById("opinionReference").value.trim();
    if (!leaf_id) {
        showToast("请选择叶片", "error");
        return;
    }
    if (!content) {
        showToast("请输入意见内容", "error");
        return;
    }
    state.collaboration.opinions.push({
        leaf_id,
        opinion_type,
        content,
        confidence,
        reference,
    });
    document.getElementById("opinionContent").value = "";
    document.getElementById("opinionReference").value = "";
    renderOpinionsList();
    showToast("意见已添加");
}

function renderOpinionsList() {
    const container = document.getElementById("opinionsList");
    const typeLabels = { text: "文字", damage: "破损", hole: "穿孔", other: "其他" };
    if (state.collaboration.opinions.length === 0) {
        container.innerHTML = '<div class="empty-state-inline">暂无标注意见</div>';
        return;
    }
    container.innerHTML = state.collaboration.opinions
        .map(
            (op, idx) => `
        <div class="opinion-item">
            <div class="opinion-header">
                <span class="opinion-tag opinion-${op.opinion_type}">${typeLabels[op.opinion_type] || op.opinion_type}</span>
                <span class="opinion-leaf">${escapeHtml(op.leaf_id)}</span>
                <span class="opinion-conf">置信度 ${(op.confidence * 100).toFixed(0)}%</span>
                <button class="annotation-item-delete" onclick="removeOpinion(${idx})">×</button>
            </div>
            <div class="opinion-content">${escapeHtml(op.content)}</div>
            ${op.reference ? `<div class="opinion-ref">参考：${escapeHtml(op.reference)}</div>` : ""}
        </div>
    `
        )
        .join("");
}

function removeOpinion(idx) {
    state.collaboration.opinions.splice(idx, 1);
    renderOpinionsList();
}

function addDispute() {
    const leaf_id = document.getElementById("disputeLeafSelect").value;
    const dispute_type = document.getElementById("disputeTypeSelect").value;
    const description = document.getElementById("disputeDescription").value.trim();
    const positionVal = document.getElementById("disputePosition").value;
    const position = positionVal !== "" ? parseInt(positionVal) : null;
    const flipped = document.getElementById("disputeFlipped").checked;
    if (!leaf_id) {
        showToast("请选择争议叶片", "error");
        return;
    }
    if (!description) {
        showToast("请输入争议描述", "error");
        return;
    }
    state.collaboration.disputes.push({
        id: uid(),
        leaf_id,
        dispute_type,
        description,
        position,
        flipped,
    });
    document.getElementById("disputeDescription").value = "";
    document.getElementById("disputePosition").value = "";
    document.getElementById("disputeFlipped").checked = false;
    renderDisputesList();
    showToast("争议说明已添加");
}

function renderDisputesList() {
    const container = document.getElementById("disputesList");
    const typeLabels = { order: "排序", annotation: "标注", classification: "分类" };
    if (state.collaboration.disputes.length === 0) {
        container.innerHTML = '<div class="empty-state-inline">暂无争议说明</div>';
        return;
    }
    container.innerHTML = state.collaboration.disputes
        .map(
            (d, idx) => `
        <div class="dispute-item">
            <div class="dispute-header">
                <span class="dispute-tag">${typeLabels[d.dispute_type] || d.dispute_type}</span>
                <span class="dispute-leaf">${escapeHtml(d.leaf_id)}</span>
                ${d.position !== null && d.position !== undefined ? `<span>位置#${d.position + 1}</span>` : ""}
                ${d.flipped ? '<span>应翻面</span>' : ""}
                <button class="annotation-item-delete" onclick="removeDispute(${idx})">×</button>
            </div>
            <div class="dispute-desc">${escapeHtml(d.description)}</div>
        </div>
    `
        )
        .join("");
}

function removeDispute(idx) {
    state.collaboration.disputes.splice(idx, 1);
    renderDisputesList();
}

async function submitCollabResult() {
    const pid = state.collaboration.currentProjectId;
    const rid = document.getElementById("submissionResearcherSelect").value;
    if (!pid || !rid) return;
    if (state.collaboration.submissionLeafOrder.length === 0) {
        showToast("请至少排一片叶片", "error");
        return;
    }
    const ordered_leaves = state.collaboration.submissionLeafOrder.map((lid, idx) => ({
        leaf_id: lid,
        order: idx,
        flipped: !!state.collaboration.submissionLeafFlipped[lid],
        rotated: 0.0,
    }));
    const payload = {
        project_id: pid,
        researcher_id: rid,
        ordered_leaves,
        annotation_opinions: state.collaboration.opinions,
        dispute_notes: state.collaboration.disputes,
        remarks: document.getElementById("submissionRemarks").value.trim(),
        is_final: document.getElementById("submissionFinal").checked,
    };
    await apiRequest(`${API_BASE}/collaboration/submissions`, {
        method: "POST",
        body: JSON.stringify(payload),
    });
    showToast("校勘结果已提交");
    state.collaboration.submissionLeafOrder = [];
    state.collaboration.submissionLeafFlipped = {};
    state.collaboration.opinions = [];
    state.collaboration.disputes = [];
    document.getElementById("submissionRemarks").value = "";
    document.getElementById("submissionFinal").checked = false;
    renderSubmissionLeafLists();
    renderOpinionsList();
    renderDisputesList();
}

function populateSummaryProjectSelect() {
    const select = document.getElementById("summaryProjectSelect");
    const current = select.value;
    select.innerHTML = '<option value="">请选择协同项目</option>';
    state.collaboration.projects.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `${p.name} (${p.id})`;
        select.appendChild(opt);
    });
    if (current && state.collaboration.projects.some((p) => p.id === current)) select.value = current;
}

async function loadSummary() {
    const pid = document.getElementById("summaryProjectSelect").value;
    if (!pid) {
        showToast("请选择协同项目", "error");
        return;
    }
    const summary = await apiRequest(`${API_BASE}/collaboration/projects/${encodeURIComponent(pid)}/summary`);
    state.collaboration.summary = summary;
    renderSummary(summary);
}

function renderSummary(s) {
    const container = document.getElementById("summaryResult");
    const submissionPct = (s.submission_rate * 100).toFixed(0);
    const agreePct = (s.overall_agreement_rate * 100).toFixed(0);

    const consensusHtml = s.leaf_consensus_list
        .map((lc) => {
            const rate = (lc.agreement_rate * 100).toFixed(0);
            const rateColor = lc.agreement_rate >= 0.8 ? "#27ae60" : lc.agreement_rate >= 0.5 ? "#f39c12" : "#c0392b";
            const positionStr = lc.agreed_position !== null && lc.agreed_position !== undefined ? `#${lc.agreed_position + 1}` : "未确定";
            const flippedStr = lc.agreed_flipped === null || lc.agreed_flipped === undefined ? "?" : lc.agreed_flipped ? "翻面" : "正";
            const disputesHtml =
                lc.disputes.length > 0
                    ? lc.disputes
                          .map((d) => `<div class="summary-dispute-note">⚠ ${escapeHtml(d.description)}</div>`)
                          .join("")
                    : "";
            const votesHtml = Object.entries(lc.position_votes || {})
                .map(([pos, cnt]) => `<span class="vote-chip">位置${parseInt(pos) + 1}:${cnt}票</span>`)
                .join("");
            return `
        <div class="consensus-item ${lc.is_controversial ? "controversial" : ""}">
            <div class="consensus-header">
                <strong class="consensus-leaf">${escapeHtml(lc.leaf_id)}</strong>
                ${lc.is_controversial ? '<span class="badge-danger">存在争议</span>' : ""}
                <span style="margin-left:auto;">投票 ${lc.total_votes}人</span>
            </div>
            <div class="consensus-body">
                <div class="consensus-row">
                    <span>共识位置：<strong>${positionStr}</strong></span>
                    <span>共识翻面：<strong>${flippedStr}</strong></span>
                </div>
                <div class="agreement-bar">
                    <div class="agreement-fill" style="width:${rate}%; background:${rateColor};"></div>
                </div>
                <div class="consensus-agreement" style="color:${rateColor};">一致率 ${rate}%</div>
                ${votesHtml ? `<div class="vote-chips">${votesHtml}</div>` : ""}
                ${disputesHtml}
            </div>
        </div>
    `;
        })
        .join("");

    const annotConsensusHtml =
        s.annotation_consensus_list.length > 0
            ? s.annotation_consensus_list
                  .map((ac) => {
                      const rate = (ac.agreement_rate * 100).toFixed(0);
                      const opinionsHtml = Object.entries(ac.opinions_by_content || {})
                          .map(([c, n]) => `<div style="font-size:12px; padding:2px 0;">“${escapeHtml(c)}” — ${n}人</div>`)
                          .join("");
                      return `
            <div class="annot-consensus-item">
                <div style="font-weight:600;">${escapeHtml(ac.leaf_id)} · ${ac.opinion_type} · 一致率 ${rate}%</div>
                <div style="margin-top:4px; color:#2c3e50;">共识：${escapeHtml(ac.consensus_content)}</div>
                <div style="margin-top:4px;">${opinionsHtml}</div>
            </div>
        `;
                  })
                  .join("")
            : '<div class="empty-state-inline">暂无标注共识数据</div>';

    container.innerHTML = `
        <div class="summary-stats-grid">
            <div class="stat-card">
                <div class="stat-num">${s.submitted_researchers}/${s.total_researchers}</div>
                <div class="stat-label">已提交研究者</div>
                <div class="stat-pct">${submissionPct}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">${s.total_leaves}</div>
                <div class="stat-label">目标叶片总数</div>
            </div>
            <div class="stat-card">
                <div class="stat-num" style="color:${s.overall_agreement_rate >= 0.7 ? "#27ae60" : s.overall_agreement_rate >= 0.5 ? "#f39c12" : "#c0392b"};">${agreePct}%</div>
                <div class="stat-label">整体排序一致率</div>
            </div>
            <div class="stat-card">
                <div class="stat-num" style="color:${s.controversial_leaf_ids.length > 0 ? "#c0392b" : "#27ae60"};">${s.controversial_leaf_ids.length}</div>
                <div class="stat-label">争议叶片数</div>
            </div>
        </div>
        ${s.controversial_leaf_ids.length ? `<div class="badge-danger-big">⚠ 存在争议叶片：${s.controversial_leaf_ids.join("、")}</div>` : ""}
        <h3 style="margin:20px 0 10px; color:#6b4423;">叶片排序共识详情</h3>
        <div class="consensus-list">${consensusHtml || '<div class="empty-state-inline">暂无提交数据</div>'}</div>
        <h3 style="margin:20px 0 10px; color:#6b4423;">标注意见共识</h3>
        <div class="annot-consensus-list">${annotConsensusHtml}</div>
        <div style="text-align:right; font-size:12px; color:#8b7355; margin-top:16px;">统计时间：${new Date(s.calculated_at).toLocaleString("zh-CN")}</div>
    `;
}

function populateDiscussionProjectSelect() {
    const select = document.getElementById("discussionProjectSelect");
    const current = select.value;
    select.innerHTML = '<option value="">请选择协同项目</option>';
    state.collaboration.projects.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `${p.name} (${p.id})`;
        select.appendChild(opt);
    });
    if (current && state.collaboration.projects.some((p) => p.id === current)) select.value = current;
}

function populateDiscussionResearcherSelect() {
    const select = document.getElementById("discussionResearcherSelect");
    const current = select.value;
    select.innerHTML = '<option value="">选择研究者</option>';
    state.collaboration.researchers.forEach((r) => {
        const opt = document.createElement("option");
        opt.value = r.id;
        opt.textContent = `${r.name} (#${r.id})`;
        select.appendChild(opt);
    });
    if (current && state.collaboration.researchers.some((r) => r.id === current)) select.value = current;
}

async function loadDiscussions() {
    const pid = document.getElementById("discussionProjectSelect").value;
    if (!pid) {
        showToast("请选择协同项目", "error");
        return;
    }
    state.collaboration.discussions = await apiRequest(`${API_BASE}/collaboration/projects/${encodeURIComponent(pid)}/discussions`);
    const project = state.collaboration.projects.find((p) => p.id === pid);
    if (project) {
        const leafSelect = document.getElementById("discussionLeafSelect");
        leafSelect.innerHTML = '<option value="">（可选）</option>';
        project.target_leaf_ids.forEach((lid) => {
            const opt = document.createElement("option");
            opt.value = lid;
            opt.textContent = lid;
            leafSelect.appendChild(opt);
        });
    }
    document.getElementById("discussionArea").style.display = "block";
    renderDiscussions();
}

function renderDiscussions() {
    const container = document.getElementById("discussionsList");
    if (state.collaboration.discussions.length === 0) {
        container.innerHTML = '<div class="empty-state-inline">暂无讨论，上方发表第一条</div>';
        return;
    }
    container.innerHTML = state.collaboration.discussions
        .map(
            (m) => {
                const time = new Date(m.created_at).toLocaleString("zh-CN");
                const tagsHtml =
                    m.tags && m.tags.length > 0
                        ? m.tags.map((t) => `<span class="disc-tag">${escapeHtml(t)}</span>`).join("")
                        : "";
                return `
        <div class="discussion-item">
            <div class="discussion-header">
                <strong class="disc-user">${escapeHtml(m.researcher_name || m.researcher_id)}</strong>
                ${m.leaf_id ? `<span class="disc-leaf">关联: ${escapeHtml(m.leaf_id)}</span>` : ""}
                ${m.is_resolved ? '<span class="disc-resolved">✅ 已解决</span>' : ""}
                <span class="disc-time">${time}</span>
            </div>
            ${tagsHtml ? `<div class="disc-tags">${tagsHtml}</div>` : ""}
            <div class="disc-content">${escapeHtml(m.content)}</div>
            ${m.resolution_note ? `<div class="disc-resolution">解决说明：${escapeHtml(m.resolution_note)}</div>` : ""}
            <div class="disc-actions">
                <button class="btn btn-xs" onclick="toggleDiscResolved('${m.id}')">${m.is_resolved ? "标记未解决" : "标记已解决"}</button>
                <button class="btn btn-xs btn-danger" onclick="deleteDiscMsg('${m.id}')">删除</button>
            </div>
        </div>
    `;
            }
        )
        .join("");
}

async function postDiscussion() {
    const pid = document.getElementById("discussionProjectSelect").value;
    const rid = document.getElementById("discussionResearcherSelect").value;
    const content = document.getElementById("discussionContent").value.trim();
    const tagsRaw = document.getElementById("discussionTags").value.trim();
    const leaf_id = document.getElementById("discussionLeafSelect").value || null;
    if (!pid || !rid) {
        showToast("请选择项目和研究者", "error");
        return;
    }
    if (!content) {
        showToast("请输入讨论内容", "error");
        return;
    }
    const tags = tagsRaw
        ? tagsRaw
              .split(/[,，]/)
              .map((t) => t.trim())
              .filter((t) => t)
        : [];
    const payload = {
        project_id: pid,
        researcher_id: rid,
        leaf_id,
        content,
        tags,
    };
    await apiRequest(`${API_BASE}/collaboration/discussions`, {
        method: "POST",
        body: JSON.stringify(payload),
    });
    document.getElementById("discussionContent").value = "";
    document.getElementById("discussionTags").value = "";
    showToast("讨论已发布");
    await loadDiscussions();
}

async function toggleDiscResolved(msgId) {
    const msg = state.collaboration.discussions.find((m) => m.id === msgId);
    if (!msg) return;
    const payload = { is_resolved: !msg.is_resolved };
    await apiRequest(`${API_BASE}/collaboration/discussions/${encodeURIComponent(msgId)}`, {
        method: "PUT",
        body: JSON.stringify(payload),
    });
    await loadDiscussions();
}

async function deleteDiscMsg(msgId) {
    if (!confirm("确定要删除这条讨论消息吗？")) return;
    await apiRequest(`${API_BASE}/collaboration/discussions/${encodeURIComponent(msgId)}`, {
        method: "DELETE",
    });
    showToast("消息已删除");
    await loadDiscussions();
}

function populateConsensusProjectSelect() {
    const select = document.getElementById("consensusProjectSelect");
    const current = select.value;
    select.innerHTML = '<option value="">请选择协同项目</option>';
    state.collaboration.projects.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `${p.name} (${p.id})`;
        select.appendChild(opt);
    });
    if (current && state.collaboration.projects.some((p) => p.id === current)) select.value = current;
}

async function loadConsensusVersions() {
    const pid = document.getElementById("consensusProjectSelect").value;
    if (!pid) {
        showToast("请选择协同项目", "error");
        return;
    }
    state.collaboration.consensusVersions = await apiRequest(
        `${API_BASE}/collaboration/projects/${encodeURIComponent(pid)}/consensus-versions`
    );
    renderConsensusVersions();
}

function renderConsensusVersions() {
    const container = document.getElementById("consensusResult");
    if (state.collaboration.consensusVersions.length === 0) {
        container.innerHTML =
            '<div class="empty-state">暂无共识版本，点击上方"自动生成共识"从提交结果创建</div>';
        return;
    }
    const project = state.collaboration.projects.find(
        (p) => p.id === document.getElementById("consensusProjectSelect").value
    );
    const researchersMap = {};
    state.collaboration.researchers.forEach((r) => (researchersMap[r.id] = r));
    container.innerHTML = state.collaboration.consensusVersions
        .map((v) => {
            const time = new Date(v.created_at).toLocaleString("zh-CN");
            const approvers = v.approved_by
                .map((id) => (researchersMap[id] ? researchersMap[id].name : id))
                .join("、");
            const leavesHtml = v.ordered_leaves
                .slice()
                .sort((a, b) => a.order - b.order)
                .map((pl, idx) => {
                    const note = v.consensus_notes[pl.leaf_id] || "";
                    const unresolved = v.unresolved_disputes.includes(pl.leaf_id);
                    return `
            <div class="consensus-leaf-item ${unresolved ? "unresolved" : ""}">
                <div class="consensus-leaf-order">${idx + 1}</div>
                <div class="consensus-leaf-info">
                    <strong>${escapeHtml(pl.leaf_id)}</strong>
                    ${pl.flipped ? '<span class="flip-tag">翻面</span>' : ""}
                    ${unresolved ? '<span class="badge-danger">争议未解决</span>' : ""}
                    ${note ? `<div class="consensus-leaf-note">${escapeHtml(note)}</div>` : ""}
                </div>
            </div>
        `;
                })
                .join("");
            return `
        <div class="consensus-version-card">
            <div class="consensus-version-header">
                <div class="consensus-version-tag">v${v.version}</div>
                <div class="consensus-version-info">
                    <h4>${escapeHtml(v.name || `共识版本 ${v.version}`)}</h4>
                    ${v.description ? `<p>${escapeHtml(v.description)}</p>` : ""}
                    <p>叶片 ${v.ordered_leaves.length} 片 · ${approvers ? `已批准: ${escapeHtml(approvers)}` : "尚未批准"}${v.is_final ? " · ✅ 最终版本" : ""}</p>
                    <p class="consensus-version-meta">创建：${time} · by ${escapeHtml(v.created_by)}</p>
                </div>
                <div class="consensus-version-actions">
                    ${project && !v.is_final
                        ? project.researcher_ids
                              .filter((rid) => !v.approved_by.includes(rid))
                              .slice(0, 3)
                              .map(
                                  (rid) =>
                                      `<button class="btn btn-xs" onclick="approveVersion('${v.id}','${rid}')">批准 (${escapeHtml(researchersMap[rid] ? researchersMap[rid].name : rid)})</button>`
                              )
                              .join("")
                        : ""}
                </div>
            </div>
            <div class="consensus-leaves-list">${leavesHtml}</div>
            ${v.unresolved_disputes.length ? `<div class="unresolved-tag">⚠ 未解决争议叶片（${v.unresolved_disputes.length}）：${v.unresolved_disputes.join("、")}</div>` : ""}
        </div>
    `;
        })
        .join("");
}

async function generateConsensusAuto() {
    const pid = document.getElementById("consensusProjectSelect").value;
    if (!pid) {
        showToast("请选择协同项目", "error");
        return;
    }
    const by = prompt("请输入创建者标识：", "system") || "system";
    const encodedPid = encodeURIComponent(pid);
    const encodedBy = encodeURIComponent(by);
    await apiRequest(`${API_BASE}/collaboration/projects/${encodedPid}/consensus-versions/generate?created_by=${encodedBy}`, {
        method: "POST",
    });
    showToast("共识版本已自动生成");
    await loadConsensusVersions();
}

async function approveVersion(versionId, researcherId) {
    const encodedV = encodeURIComponent(versionId);
    const encodedR = encodeURIComponent(researcherId);
    await apiRequest(`${API_BASE}/collaboration/consensus-versions/${encodedV}/approve?researcher_id=${encodedR}`, {
        method: "POST",
    });
    showToast("已批准");
    await loadConsensusVersions();
}

function initCollaboration() {
    initCollabSubtabs();
    initSubmissionControls();

    document.getElementById("addResearcherBtn").addEventListener("click", openAddResearcherModal);
    document.getElementById("researcherForm").addEventListener("submit", submitResearcherForm);
    document.getElementById("addProjectBtn").addEventListener("click", openAddProjectModal);
    document.getElementById("projectForm").addEventListener("submit", submitProjectForm);
    document.getElementById("deleteProjectBtn").addEventListener("click", deleteCurrentProject);
    document.getElementById("viewProjectSubmissions").addEventListener("click", viewCurrentProjectSubmissions);

    document.getElementById("loadSubmissionProjectBtn").addEventListener("click", loadSubmissionProject);
    document.getElementById("addLeafToSubmission").addEventListener("click", addLeafToSubmission);
    document.getElementById("removeLeafFromSubmission").addEventListener("click", removeLeafFromSubmission);
    document.getElementById("submissionLeafUp").addEventListener("click", submissionLeafMoveUp);
    document.getElementById("submissionLeafDown").addEventListener("click", submissionLeafMoveDown);
    document.getElementById("addOpinionBtn").addEventListener("click", addOpinion);
    document.getElementById("addDisputeBtn").addEventListener("click", addDispute);
    document.getElementById("submitCollabBtn").addEventListener("click", submitCollabResult);

    document.getElementById("loadSummaryBtn").addEventListener("click", loadSummary);
    document.getElementById("loadDiscussionsBtn").addEventListener("click", loadDiscussions);
    document.getElementById("postDiscussionBtn").addEventListener("click", postDiscussion);
    document.getElementById("generateConsensusBtn").addEventListener("click", generateConsensusAuto);
    document.getElementById("loadConsensusBtn").addEventListener("click", loadConsensusVersions);
}

async function init() {
    initTabs();
    initModals();
    initSortControls();
    initAnnotateTools();
    initCompare();
    initAudit();
    initCollaboration();

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
        await loadResearchers();
        await loadCollabProjects();
    } catch (e) {
        console.error("加载数据失败:", e);
    }
}

document.addEventListener("DOMContentLoaded", init);
