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
};

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

function showToast(message, type = "success") {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => {
        toast.className = "toast";
    }, 3000);
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
            if (tabId === "sort") {
                populateStartLeafSelect();
            }
        });
    });
}

function initModals() {
    document.querySelectorAll(".close, [data-close]").forEach((el) => {
        el.addEventListener("click", () => {
            const modalId = el.dataset.modal || el.dataset.close;
            document.getElementById(modalId).classList.remove("active");
        });
    });

    document.querySelectorAll(".modal").forEach((modal) => {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) {
                modal.classList.remove("active");
            }
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
            <div class="leaf-dims">尺寸：${leaf.length} × ${leaf.width} mm</div>
            <div class="leaf-holes">穿孔数：${leaf.holes.length}${leaf.holes.length > 0 ? " 个" : ""}</div>
            ${leaf.holes.length > 0 ? `<div class="leaf-holes">孔位：${leaf.holes.map((h) => `(${h.x}, ${h.y})`).join(", ")}</div>` : ""}
            ${leaf.residual_text ? `<div class="leaf-text-preview">${escapeHtml(leaf.residual_text)}</div>` : ""}
            ${leaf.damage ? `<div class="leaf-damage">⚠ ${escapeHtml(leaf.damage)}</div>` : ""}
            <div class="leaf-card-actions">
                <button class="btn btn-secondary" onclick="editLeaf('${leaf.id}')">编辑</button>
                <button class="btn btn-danger" onclick="deleteLeaf('${leaf.id}')">删除</button>
            </div>
        </div>
    `
        )
        .join("");
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

async function openAddLeafModal() {
    state.editingLeafId = null;
    document.getElementById("leafModalTitle").textContent = "添加叶片";
    document.getElementById("leafForm").reset();
    document.getElementById("leafId").disabled = false;
    document.getElementById("leafModal").classList.add("active");
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
    document.getElementById("leafModal").classList.add("active");
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
                parseErrors.push(`第 ${i + 1} 行格式错误：需要用逗号分隔两个数字，例如 "10.5, 20.3"`);
                continue;
            }
            const x = parseFloat(parts[0]);
            const y = parseFloat(parts[1]);
            if (isNaN(x) || isNaN(y)) {
                parseErrors.push(`第 ${i + 1} 行格式错误："${line}" 不是有效的数字`);
                continue;
            }
            holes.push({ x, y });
        }
    }

    if (parseErrors.length > 0) {
        showToast("穿孔坐标格式错误：\n" + parseErrors.join("\n"), "error");
        return;
    }

    const leafLength = parseFloat(document.getElementById("leafLength").value);
    const leafWidth = parseFloat(document.getElementById("leafWidth").value);

    for (let i = 0; i < holes.length; i++) {
        const h = holes[i];
        if (h.x < 0 || h.x > leafWidth) {
            parseErrors.push(`第 ${i + 1} 个穿孔 X 坐标 ${h.x} 超出宽度范围 [0, ${leafWidth}]`);
        }
        if (h.y < 0 || h.y > leafLength) {
            parseErrors.push(`第 ${i + 1} 个穿孔 Y 坐标 ${h.y} 超出长度范围 [0, ${leafLength}]`);
        }
    }

    if (parseErrors.length > 0) {
        showToast("穿孔坐标超出范围：\n" + parseErrors.join("\n"), "error");
        return;
    }

    const oldLeaf = state.editingLeafId ? state.leaves.find((l) => l.id === state.editingLeafId) : null;
    const residualTextChanged = oldLeaf && oldLeaf.residual_text !== document.getElementById("leafText").value.trim();

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

    document.getElementById("leafModal").classList.remove("active");
    await loadLeaves();
    await loadPlans();

    if (residualTextChanged || state.editingLeafId) {
        const affectedPlans = state.plans.filter((p) => p.leaves.some((l) => l.leaf_id === (state.editingLeafId || payload.id)));
        for (const plan of affectedPlans) {
            try {
                await apiRequest(`${API_BASE}/plans/${plan.id}/recalculate`, { method: "POST" });
            } catch (e) {}
        }
        await loadPlans();
        if (state.currentViewingPlanId) {
            await viewPlan(state.currentViewingPlanId);
        }

        const sortTab = document.getElementById("sort");
        if (sortTab.classList.contains("active") && document.getElementById("sortResult").innerHTML.trim() !== "") {
            await runSort();
        }
    }
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
    document.getElementById("planModal").classList.add("active");
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
    document.getElementById("planDetailModal").classList.remove("active");
    document.getElementById("planModal").classList.add("active");
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
                  .map(
                      (lid, idx) => {
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
                      }
                  )
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
    if (idx >= 0) {
        state.planLeafOrder.splice(idx, 1);
    }
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

    document.getElementById("planModal").classList.remove("active");
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

    document.getElementById("planDetailModal").classList.add("active");
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
    document.getElementById("planDetailModal").classList.remove("active");
    await loadPlans();
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
    if (startId) {
        url += `&start_leaf_id=${encodeURIComponent(startId)}`;
    }

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

async function init() {
    initTabs();
    initModals();
    initSortControls();

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

    try {
        await loadLeaves();
        await loadPlans();
    } catch (e) {
        console.error("加载数据失败:", e);
    }
}

document.addEventListener("DOMContentLoaded", init);
