// 水质检测报告系统 V2 - 前端JavaScript

// 全局状态
const AppState = {
    currentUser: null,
    sampleTypes: [],
    indicators: [],
    indicatorGroups: [],
    companies: [],
    reports: [],
    reportTemplates: [],
    editingReportId: null  // 当前正在编辑的报告ID
};

// ==================== 工具函数 ====================
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toastContainer');
    const toastId = 'toast_' + Date.now();
    const bgClass = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-warning';

    const toastHTML = `
        <div class="toast align-items-center text-white ${bgClass} border-0" role="alert" id="${toastId}">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
    toast.show();
    toastElement.addEventListener('hidden.bs.toast', () => toastElement.remove());
}

async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || '请求失败');
        }

        return data;
    } catch (error) {
        showToast(error.message, 'error');
        throw error;
    }
}

function formatDateTime(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${year}年${month}月${day}日 ${hours}:${minutes}:${seconds}`;
}

function formatDate(dateString) {
    if (!dateString) return '';
    // Handle YYYY-MM-DD format directly
    const match = dateString.match(/(\d{4})-(\d{2})-(\d{2})/);
    if (match) {
        return `${match[1]}年${match[2]}月${match[3]}日`;
    }
    // Fallback to Date object parsing
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}年${month}月${day}日`;
}

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', async () => {
    await loadCurrentUser();
    updateUIByRole();
    await loadInitialData();
    bindEvents();

    // 设置默认检测日期为今天
    document.getElementById('detectionDate').valueAsDate = new Date();
});

async function loadCurrentUser() {
    try {
        const data = await apiRequest('/api/auth/current-user');
        AppState.currentUser = data.user;
        document.getElementById('currentUsername').textContent = data.user.username;
        document.getElementById('currentUserRole').textContent = data.user.role === 'admin' ? '管理员' : '填写人';
    } catch (error) {
        window.location.href = '/login';
    }
}

function updateUIByRole() {
    if (!AppState.currentUser) return;

    if (AppState.currentUser.role !== 'admin') {
        document.getElementById('templateTabLi').style.display = 'none';
        document.getElementById('dataTabLi').style.display = 'none';

        // 切换到报告填写标签页
        const reportTab = new bootstrap.Tab(document.getElementById('report-tab'));
        reportTab.show();
    }
}

async function loadInitialData() {
    await Promise.all([
        loadSampleTypes(),
        loadIndicators(),
        loadIndicatorGroups(),
        loadCompanies(),
        loadReportTemplates()
    ]);
}

// ==================== 事件绑定 ====================
function bindEvents() {
    // 认证相关
    document.getElementById('logoutBtn').addEventListener('click', logout);

    // 样品类型管理
    document.getElementById('addSampleTypeBtn')?.addEventListener('click', showAddSampleTypeModal);
    document.getElementById('exportSampleTypesBtn')?.addEventListener('click', exportSampleTypesExcel);
    document.getElementById('importSampleTypesBtn')?.addEventListener('click', showImportSampleTypesModal);

    // 检测指标管理
    document.getElementById('addIndicatorBtn')?.addEventListener('click', showAddIndicatorModal);
    document.getElementById('exportIndicatorsBtn')?.addEventListener('click', exportIndicatorsExcel);
    document.getElementById('importIndicatorsBtn')?.addEventListener('click', showImportIndicatorsModal);

    // 模板配置（已禁用 - 功能已整合到样品类型管理中）
    // document.getElementById('configTemplateBtn')?.addEventListener('click', configTemplate);
    // document.getElementById('exportTemplateBtn')?.addEventListener('click', exportTemplate);

    // 新建报告流程
    document.getElementById('reportTemplate')?.addEventListener('change', onNewReportTemplateChange);
    document.getElementById('downloadTemplateExcelBtn')?.addEventListener('click', downloadTemplateExcel);
    document.getElementById('templateExcelFile')?.addEventListener('change', onTemplateExcelUploaded);
    document.getElementById('reportSampleType')?.addEventListener('change', onNewSampleTypeChange);
    document.getElementById('downloadDetectionExcelBtn')?.addEventListener('click', downloadDetectionExcel);
    document.getElementById('detectionExcelFile')?.addEventListener('change', onDetectionExcelUploaded);
    document.getElementById('parseAndPreviewBtn')?.addEventListener('click', parseAndPreview);
    document.getElementById('saveDraftBtn')?.addEventListener('click', saveDraftFromPreview);
    document.getElementById('submitReportBtn')?.addEventListener('click', submitReportFromPreview);
    document.getElementById('generateDirectBtn')?.addEventListener('click', generateReportDirect);
    document.getElementById('resetFormBtn')?.addEventListener('click', resetNewReportForm);

    // 待提交报告
    document.getElementById('searchPendingBtn')?.addEventListener('click', loadPendingReports);
    document.getElementById('refreshPendingBtn')?.addEventListener('click', loadPendingReports);

    // 已提交报告
    document.getElementById('searchSubmittedBtn')?.addEventListener('click', loadSubmittedReports);
    document.getElementById('refreshSubmittedBtn')?.addEventListener('click', loadSubmittedReports);

    // 报告审核
    document.getElementById('searchReviewBtn')?.addEventListener('click', loadReviewReports);
    document.getElementById('refreshReviewBtn')?.addEventListener('click', loadReviewReports);

    // 报告生成
    document.getElementById('searchGenReportBtn')?.addEventListener('click', loadGenReports);
    document.getElementById('refreshGenReportBtn')?.addEventListener('click', loadGenReports);

    // 报告查询
    document.getElementById('searchReportBtn')?.addEventListener('click', searchReports);
    document.getElementById('refreshReportBtn')?.addEventListener('click', () => loadReports());

    // 数据管理
    document.getElementById('createBackupBtn')?.addEventListener('click', createBackup);
    document.getElementById('refreshLogsBtn')?.addEventListener('click', loadLogs);
    document.getElementById('addUserBtn')?.addEventListener('click', showAddUserModal);

    // 标签页切换事件
    document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', (event) => {
            const targetId = event.target.getAttribute('data-bs-target');
            if (targetId === '#query') {
                loadReports();
            } else if (targetId === '#data') {
                loadBackups();
                loadLogs();
                loadUsers();
            } else if (targetId === '#pending-reports') {
                loadPendingReports();
            } else if (targetId === '#submitted-reports') {
                loadSubmittedReports();
            } else if (targetId === '#review') {
                loadReviewReports();
            } else if (targetId === '#generate') {
                loadGenReports();
            }
        });
    });
}

// ==================== 认证相关 ====================
async function logout() {
    try {
        await apiRequest('/api/auth/logout', { method: 'POST' });
        window.location.href = '/login';
    } catch (error) {
        console.error('退出失败:', error);
    }
}

// ==================== 样品类型管理 ====================
async function loadSampleTypes() {
    try {
        const data = await apiRequest('/api/sample-types');
        AppState.sampleTypes = data;

        // 更新下拉框（templateSampleType已移除，功能整合到样品类型管理中）
        const selects = ['reportSampleType'];
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            select.innerHTML = '<option value="">请选择...</option>';
            data.forEach(st => {
                select.innerHTML += `<option value="${st.id}">${st.name}</option>`;
            });
        });

        updateSampleTypesList();
    } catch (error) {
        console.error('加载样品类型失败:', error);
    }
}

function updateSampleTypesList() {
    const tbody = document.getElementById('sampleTypesList');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (AppState.sampleTypes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无数据</td></tr>';
        return;
    }

    AppState.sampleTypes.forEach(st => {
        tbody.innerHTML += `
            <tr>
                <td>${st.name}</td>
                <td><span class="badge bg-primary">${st.code}</span></td>
                <td>${st.description || '-'}</td>
                <td>
                    <button class="btn btn-sm btn-warning me-1" onclick="showEditSampleTypeModal(${st.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteSampleType(${st.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });
}

function showAddSampleTypeModal() {
    const modalHTML = `
        <div class="modal fade" id="addSampleTypeModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">添加样品类型</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="addSampleTypeForm">
                            <div class="mb-3">
                                <label class="form-label">名称 <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="stName" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">代码 <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="stCode" required placeholder="如: CCW">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">说明</label>
                                <textarea class="form-control" id="stDescription" rows="3"></textarea>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="addSampleType()">保存</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('modalContainer').innerHTML = modalHTML;
    const modal = new bootstrap.Modal(document.getElementById('addSampleTypeModal'));
    modal.show();
}

async function addSampleType() {
    const name = document.getElementById('stName').value;
    const code = document.getElementById('stCode').value;
    const description = document.getElementById('stDescription').value;

    try {
        await apiRequest('/api/sample-types', {
            method: 'POST',
            body: JSON.stringify({ name, code, description })
        });

        showToast('样品类型添加成功');
        bootstrap.Modal.getInstance(document.getElementById('addSampleTypeModal')).hide();
        await loadSampleTypes();
    } catch (error) {
        console.error('添加样品类型失败:', error);
    }
}

function showEditSampleTypeModal(id) {
    const sampleType = AppState.sampleTypes.find(st => st.id === id);
    if (!sampleType) return;

    const modalHTML = `
        <div class="modal fade" id="editSampleTypeModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">修改样品类型</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="editSampleTypeForm">
                            <div class="mb-3">
                                <label class="form-label">名称 <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="estName" value="${sampleType.name}" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">代码 <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="estCode" value="${sampleType.code}" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">说明</label>
                                <textarea class="form-control" id="estDescription" rows="3">${sampleType.description || ''}</textarea>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="updateSampleType(${id})">保存</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('modalContainer').innerHTML = modalHTML;
    const modal = new bootstrap.Modal(document.getElementById('editSampleTypeModal'));
    modal.show();
}

async function updateSampleType(id) {
    const name = document.getElementById('estName').value;
    const code = document.getElementById('estCode').value;
    const description = document.getElementById('estDescription').value;

    try {
        await apiRequest(`/api/sample-types/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ name, code, description })
        });

        showToast('样品类型更新成功');
        bootstrap.Modal.getInstance(document.getElementById('editSampleTypeModal')).hide();
        await loadSampleTypes();
    } catch (error) {
        console.error('更新样品类型失败:', error);
    }
}

async function deleteSampleType(id) {
    if (!confirm('确定要删除这个样品类型吗？')) return;

    try {
        await apiRequest(`/api/sample-types/${id}`, { method: 'DELETE' });
        showToast('样品类型删除成功');
        await loadSampleTypes();
    } catch (error) {
        console.error('删除样品类型失败:', error);
    }
}

async function exportSampleTypesExcel() {
    try {
        const response = await fetch('/api/sample-types/export/excel');
        if (!response.ok) throw new Error('导出失败');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = '样品类型.xlsx';
        a.click();

        showToast('样品类型导出成功');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

function showImportSampleTypesModal() {
    const modalHTML = `
        <div class="modal fade" id="importSampleTypesModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">导入样品类型</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">选择Excel文件</label>
                            <input type="file" class="form-control" id="sampleTypesFile" accept=".xlsx,.xls">
                        </div>
                        <div class="alert alert-info">
                            <small>
                                <strong>格式说明：</strong><br>
                                Excel应包含以下列：样品类型名称、样品代码、说明<br>
                                建议先导出现有数据作为模板参考
                            </small>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="importSampleTypesExcel()">导入</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('modalContainer').innerHTML = modalHTML;
    const modal = new bootstrap.Modal(document.getElementById('importSampleTypesModal'));
    modal.show();
}

async function importSampleTypesExcel() {
    const fileInput = document.getElementById('sampleTypesFile');
    const file = fileInput.files[0];

    if (!file) {
        showToast('请选择文件', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/sample-types/import/excel', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || '导入失败');
        }

        let message = data.message;
        if (data.errors && data.errors.length > 0) {
            message += '\n\n错误信息：\n' + data.errors.join('\n');
        }

        showToast(message);
        bootstrap.Modal.getInstance(document.getElementById('importSampleTypesModal')).hide();
        await loadSampleTypes();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ==================== 报告模板管理 ====================
async function loadReportTemplates() {
    try {
        const data = await apiRequest('/api/report-templates');
        AppState.reportTemplates = data;

        // 更新报告模板下拉框
        const select = document.getElementById('reportTemplate');
        if (select) {
            select.innerHTML = '<option value="">请选择报告模板...</option>';
            data.forEach(template => {
                const sampleTypeInfo = template.sample_type_name ? ` (${template.sample_type_name})` : '';
                select.innerHTML += `<option value="${template.id}">${template.name}${sampleTypeInfo}</option>`;
            });
        }
    } catch (error) {
        console.error('加载报告模板失败:', error);
    }
}

// ==================== 检测指标管理 ====================
async function loadIndicators() {
    try {
        const data = await apiRequest('/api/indicators');
        AppState.indicators = data;
        updateIndicatorsList();
    } catch (error) {
        console.error('加载检测指标失败:', error);
    }
}

function updateIndicatorsList() {
    const tbody = document.getElementById('indicatorsList');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (AppState.indicators.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无数据</td></tr>';
        return;
    }

    AppState.indicators.forEach(ind => {
        tbody.innerHTML += `
            <tr>
                <td>${ind.name}</td>
                <td>${ind.unit || '-'}</td>
                <td><span class="badge bg-info">${ind.group_name || '未分组'}</span></td>
                <td>
                    <button class="btn btn-sm btn-warning me-1" onclick="showEditIndicatorModal(${ind.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteIndicator(${ind.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });
}

async function loadIndicatorGroups() {
    try {
        const data = await apiRequest('/api/indicator-groups');
        AppState.indicatorGroups = data;
    } catch (error) {
        console.error('加载检测项目分组失败:', error);
    }
}

function showAddIndicatorModal() {
    const groupOptions = AppState.indicatorGroups.map(g =>
        `<option value="${g.id}">${g.name}</option>`
    ).join('');

    const modalHTML = `
        <div class="modal fade" id="addIndicatorModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">添加检测指标</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="addIndicatorForm">
                            <div class="mb-3">
                                <label class="form-label">名称 <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="indName" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">单位</label>
                                <input type="text" class="form-control" id="indUnit" placeholder="如: mg/L">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">分组</label>
                                <select class="form-select" id="indGroup">
                                    <option value="">不分组</option>
                                    ${groupOptions}
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">默认值</label>
                                <input type="text" class="form-control" id="indDefaultValue">
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="addIndicator()">保存</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('modalContainer').innerHTML = modalHTML;
    const modal = new bootstrap.Modal(document.getElementById('addIndicatorModal'));
    modal.show();
}

async function addIndicator() {
    const name = document.getElementById('indName').value;
    const unit = document.getElementById('indUnit').value;
    const group_id = document.getElementById('indGroup').value || null;
    const default_value = document.getElementById('indDefaultValue').value;

    try {
        await apiRequest('/api/indicators', {
            method: 'POST',
            body: JSON.stringify({ name, unit, group_id, default_value, sort_order: 0 })
        });

        showToast('检测指标添加成功');
        bootstrap.Modal.getInstance(document.getElementById('addIndicatorModal')).hide();
        await loadIndicators();
    } catch (error) {
        console.error('添加检测指标失败:', error);
    }
}

function showEditIndicatorModal(id) {
    const indicator = AppState.indicators.find(ind => ind.id === id);
    if (!indicator) return;

    const groupOptions = AppState.indicatorGroups.map(g =>
        `<option value="${g.id}" ${indicator.group_id === g.id ? 'selected' : ''}>${g.name}</option>`
    ).join('');

    const modalHTML = `
        <div class="modal fade" id="editIndicatorModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">修改检测指标</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="editIndicatorForm">
                            <div class="mb-3">
                                <label class="form-label">名称 <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="eindName" value="${indicator.name}" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">单位</label>
                                <input type="text" class="form-control" id="eindUnit" value="${indicator.unit || ''}" placeholder="如: mg/L">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">分组</label>
                                <select class="form-select" id="eindGroup">
                                    <option value="">不分组</option>
                                    ${groupOptions}
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">默认值</label>
                                <input type="text" class="form-control" id="eindDefaultValue" value="${indicator.default_value || ''}">
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="updateIndicator(${id})">保存</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('modalContainer').innerHTML = modalHTML;
    const modal = new bootstrap.Modal(document.getElementById('editIndicatorModal'));
    modal.show();
}

async function updateIndicator(id) {
    const name = document.getElementById('eindName').value;
    const unit = document.getElementById('eindUnit').value;
    const group_id = document.getElementById('eindGroup').value || null;
    const default_value = document.getElementById('eindDefaultValue').value;

    try {
        await apiRequest(`/api/indicators/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ name, unit, group_id, default_value, sort_order: 0 })
        });

        showToast('检测指标更新成功');
        bootstrap.Modal.getInstance(document.getElementById('editIndicatorModal')).hide();
        await loadIndicators();
    } catch (error) {
        console.error('更新检测指标失败:', error);
    }
}

async function deleteIndicator(id) {
    if (!confirm('确定要删除这个检测指标吗？')) return;

    try {
        await apiRequest(`/api/indicators/${id}`, { method: 'DELETE' });
        showToast('检测指标删除成功');
        await loadIndicators();
    } catch (error) {
        console.error('删除检测指标失败:', error);
    }
}

async function exportIndicatorsExcel() {
    try {
        const response = await fetch('/api/indicators/export/excel');
        if (!response.ok) throw new Error('导出失败');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = '检测指标.xlsx';
        a.click();

        showToast('检测指标导出成功');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

function showImportIndicatorsModal() {
    const modalHTML = `
        <div class="modal fade" id="importIndicatorsModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">导入检测指标</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">选择Excel文件</label>
                            <input type="file" class="form-control" id="indicatorsFile" accept=".xlsx,.xls">
                        </div>
                        <div class="alert alert-info">
                            <small>
                                <strong>格式说明：</strong><br>
                                Excel应包含以下列：指标名称、单位、默认值、限值、检测方法、所属分组、排序、备注<br>
                                建议先导出现有数据作为模板参考
                            </small>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="importIndicatorsExcel()">导入</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('modalContainer').innerHTML = modalHTML;
    const modal = new bootstrap.Modal(document.getElementById('importIndicatorsModal'));
    modal.show();
}

async function importIndicatorsExcel() {
    const fileInput = document.getElementById('indicatorsFile');
    const file = fileInput.files[0];

    if (!file) {
        showToast('请选择文件', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/indicators/import/excel', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || '导入失败');
        }

        let message = data.message;
        if (data.errors && data.errors.length > 0) {
            message += '\n\n错误信息：\n' + data.errors.join('\n');
        }

        showToast(message);
        bootstrap.Modal.getInstance(document.getElementById('importIndicatorsModal')).hide();
        await loadIndicators();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ==================== 公司管理 ====================
async function loadCompanies() {
    try {
        const data = await apiRequest('/api/companies');
        AppState.companies = data;

        // 更新下拉框
        const selects = ['reportCompany', 'searchCompany'];
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            const currentValue = select.value;
            select.innerHTML = '<option value="">请选择...</option>';
            data.forEach(company => {
                select.innerHTML += `<option value="${company.id}">${company.name}</option>`;
            });
            select.value = currentValue;
        });
    } catch (error) {
        console.error('加载公司列表失败:', error);
    }
}

// ==================== 模板配置（已禁用 - 功能已整合到样品类型管理中）====================
/* 已禁用：模板配置功能已整合到样品类型管理模块中
async function configTemplate() {
    const sampleTypeId = document.getElementById('templateSampleType').value;
    if (!sampleTypeId) {
        showToast('请先选择样品类型', 'warning');
        return;
    }

    try {
        const data = await apiRequest(`/api/template-indicators?sample_type_id=${sampleTypeId}`);
        showTemplateConfigModal(sampleTypeId, data);
    } catch (error) {
        console.error('加载模板配置失败:', error);
    }
}

function showTemplateConfigModal(sampleTypeId, currentIndicators) {
    const currentIds = currentIndicators.map(ti => ti.indicator_id);

    // 按分组组织检测指标
    const groupedIndicators = {};
    AppState.indicators.forEach(ind => {
        const groupName = ind.group_name || '未分组';
        if (!groupedIndicators[groupName]) {
            groupedIndicators[groupName] = [];
        }
        groupedIndicators[groupName].push(ind);
    });

    // HTML转义函数
    const escapeHtml = (text) => {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };

    // 清理和截断文本
    const clean = (text, maxLen = 50) => {
        if (!text || text === 'null' || text === 'undefined') return '-';
        const str = String(text).replace(/[\r\n\t]+/g, ' ').trim();
        const truncated = str.length > maxLen ? str.substring(0, maxLen) + '...' : str;
        return escapeHtml(truncated);
    };

    // 生成分组显示的HTML
    let indicatorCheckboxes = '';
    for (const [groupName, indicators] of Object.entries(groupedIndicators)) {
        const escapedGroupName = escapeHtml(groupName);

        indicatorCheckboxes += `<div class="mb-3 indicator-group">`;
        indicatorCheckboxes += `<h6 class="text-primary border-bottom pb-2"><i class="bi bi-folder"></i> ${escapedGroupName} <span class="badge bg-secondary">${indicators.length}项</span></h6>`;
        indicatorCheckboxes += `<div class="table-responsive"><table class="table table-sm table-hover table-bordered">`;
        indicatorCheckboxes += `<thead class="table-light"><tr>`;
        indicatorCheckboxes += `<th style="width:50px" class="text-center"><input type="checkbox" class="form-check-input group-select-all" data-group="${escapedGroupName}"></th>`;
        indicatorCheckboxes += `<th style="width:150px">指标名称</th>`;
        indicatorCheckboxes += `<th style="width:70px">单位</th>`;
        indicatorCheckboxes += `<th style="width:100px">分组</th>`;
        indicatorCheckboxes += `<th style="width:100px">限值</th>`;
        indicatorCheckboxes += `<th style="width:200px">检测方法</th>`;
        indicatorCheckboxes += `<th style="width:80px">默认值</th>`;
        indicatorCheckboxes += `<th>备注</th>`;
        indicatorCheckboxes += `</tr></thead><tbody>`;

        indicators.forEach(ind => {
            const checked = currentIds.includes(ind.id) ? 'checked' : '';
            const name = clean(ind.name, 25);
            const unit = clean(ind.unit, 10);
            const group = ind.group_name ? clean(ind.group_name, 15) : '未分组';
            const limit = clean(ind.limit_value, 20);
            const method = clean(ind.detection_method, 40);
            const defVal = clean(ind.default_value, 15);
            const rem = clean(ind.remark, 30);

            // 调试：检查某个具体指标的数据
            if (ind.name && ind.name.includes('总磷')) {
                console.log('总磷指标数据:', {
                    name: name,
                    unit: unit,
                    group: group,
                    limit: limit,
                    method: method,
                    defVal: defVal,
                    rem: rem,
                    原始数据: ind
                });
            }

            const row = document.createElement('tr');
            row.className = 'indicator-row';

            // 创建8个td
            const td1 = document.createElement('td');
            td1.className = 'text-center';
            td1.innerHTML = `<input class="form-check-input indicator-checkbox" type="checkbox" value="${ind.id}" ${checked}>`;

            const td2 = document.createElement('td');
            td2.textContent = name;

            const td3 = document.createElement('td');
            td3.textContent = unit;

            const td4 = document.createElement('td');
            td4.innerHTML = `<span class="badge bg-info">${group}</span>`;

            const td5 = document.createElement('td');
            td5.textContent = limit;

            const td6 = document.createElement('td');
            td6.textContent = method;

            const td7 = document.createElement('td');
            td7.textContent = defVal;

            const td8 = document.createElement('td');
            td8.textContent = rem;

            row.appendChild(td1);
            row.appendChild(td2);
            row.appendChild(td3);
            row.appendChild(td4);
            row.appendChild(td5);
            row.appendChild(td6);
            row.appendChild(td7);
            row.appendChild(td8);

            indicatorCheckboxes += row.outerHTML;
        });

        indicatorCheckboxes += `</tbody></table></div></div>`;
    }

    const modalHTML = `
        <div class="modal fade" id="configTemplateModal" tabindex="-1">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-wrench"></i> 配置检测项目
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row mb-3">
                            <div class="col-md-8">
                                <div class="input-group">
                                    <span class="input-group-text"><i class="bi bi-search"></i></span>
                                    <input type="text" class="form-control" id="indicatorSearchInput" placeholder="搜索分组名称、指标名称、单位、限值、检测方法或备注...">
                                </div>
                            </div>
                            <div class="col-md-4">
                                <button type="button" class="btn btn-outline-primary" id="selectAllIndicators">
                                    <i class="bi bi-check-square"></i> 全选
                                </button>
                                <button type="button" class="btn btn-outline-secondary" id="deselectAllIndicators">
                                    <i class="bi bi-square"></i> 取消全选
                                </button>
                            </div>
                        </div>
                        <div class="alert alert-info mb-3">
                            <i class="bi bi-info-circle"></i>
                            选择该样品类型需要检测的项目。可以使用搜索框按分组名称或指标内容筛选，也可以点击分组标题旁的复选框批量选择整个分组。
                        </div>
                        <div id="indicatorsList" style="max-height: 500px; overflow-y: auto;">
                            ${indicatorCheckboxes}
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="saveTemplateConfig(${sampleTypeId})">
                            <i class="bi bi-check-lg"></i> 保存配置
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('modalContainer').innerHTML = modalHTML;
    const modal = new bootstrap.Modal(document.getElementById('configTemplateModal'));
    modal.show();

    // 绑定搜索功能 - 支持按分组名称搜索
    document.getElementById('indicatorSearchInput').addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase();
        const groups = document.querySelectorAll('.indicator-group');

        groups.forEach(group => {
            const groupTitle = group.querySelector('h6').textContent.toLowerCase();
            const rows = group.querySelectorAll('.indicator-row');

            // 如果搜索词匹配分组名称，显示该分组的所有项目
            if (groupTitle.includes(searchTerm)) {
                rows.forEach(row => {
                    row.style.display = '';
                });
                group.style.display = '';
            } else {
                // 否则按行内容搜索
                let hasVisibleRow = false;
                rows.forEach(row => {
                    const text = row.textContent.toLowerCase();
                    if (text.includes(searchTerm)) {
                        row.style.display = '';
                        hasVisibleRow = true;
                    } else {
                        row.style.display = 'none';
                    }
                });
                group.style.display = hasVisibleRow ? '' : 'none';
            }
        });
    });

    // 绑定全选功能
    document.getElementById('selectAllIndicators').addEventListener('click', function() {
        document.querySelectorAll('#indicatorsList .indicator-checkbox').forEach(cb => {
            const row = cb.closest('.indicator-row');
            if (row && row.style.display !== 'none') {
                cb.checked = true;
            }
        });
    });

    // 绑定取消全选功能
    document.getElementById('deselectAllIndicators').addEventListener('click', function() {
        document.querySelectorAll('#indicatorsList .indicator-checkbox').forEach(cb => {
            cb.checked = false;
        });
    });

    // 绑定分组全选功能
    document.querySelectorAll('.group-select-all').forEach(groupCheckbox => {
        groupCheckbox.addEventListener('change', function() {
            const groupElement = this.closest('.indicator-group');
            const checkboxes = groupElement.querySelectorAll('.indicator-checkbox');
            checkboxes.forEach(cb => {
                const row = cb.closest('.indicator-row');
                if (row && row.style.display !== 'none') {
                    cb.checked = this.checked;
                }
            });
        });
    });
}

async function saveTemplateConfig(sampleTypeId) {
    const checkboxes = document.querySelectorAll('#configTemplateModal .indicator-checkbox:checked');
    const selectedIds = Array.from(checkboxes).map(cb => parseInt(cb.value));

    try {
        // 删除现有配置
        const current = await apiRequest(`/api/template-indicators?sample_type_id=${sampleTypeId}`);
        for (const ti of current) {
            await apiRequest(`/api/template-indicators/${ti.id}`, { method: 'DELETE' });
        }

        // 添加新配置
        for (let i = 0; i < selectedIds.length; i++) {
            await apiRequest('/api/template-indicators', {
                method: 'POST',
                body: JSON.stringify({
                    sample_type_id: sampleTypeId,
                    indicator_id: selectedIds[i],
                    is_required: false,
                    sort_order: i
                })
            });
        }

        showToast('模板配置保存成功');
        bootstrap.Modal.getInstance(document.getElementById('configTemplateModal')).hide();
    } catch (error) {
        console.error('保存模板配置失败:', error);
    }
}

async function exportTemplate() {
    const sampleTypeId = document.getElementById('templateSampleType').value;
    if (!sampleTypeId) {
        showToast('请先选择样品类型', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/templates/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sample_type_id: sampleTypeId })
        });

        if (!response.ok) throw new Error('导出失败');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `template_${Date.now()}.json`;
        a.click();

        showToast('模板导出成功');
    } catch (error) {
        showToast(error.message, 'error');
    }
}
*/

// ==================== 报告填写 ====================
async function onReportTemplateChange() {
    const templateId = document.getElementById('reportTemplate').value;
    const formContent = document.getElementById('reportFormContent');
    const templateFieldsArea = document.getElementById('templateFieldsArea');
    const sampleTypeSelect = document.getElementById('reportSampleType');

    if (!templateId) {
        formContent.style.display = 'none';
        sampleTypeSelect.disabled = true;
        sampleTypeSelect.innerHTML = '<option value="">请先选择报告模板...</option>';
        return;
    }

    try {
        // 启用样品类型选择框
        sampleTypeSelect.disabled = false;
        sampleTypeSelect.innerHTML = '<option value="">请选择样品类型...</option>';

        // 加载样品类型列表
        AppState.sampleTypes.forEach(st => {
            const option = document.createElement('option');
            option.value = st.id;
            option.textContent = st.name;
            sampleTypeSelect.appendChild(option);
        });

        // 先获取模板信息
        const templateInfo = await apiRequest(`/api/report-templates/${templateId}`);
        const template = templateInfo.template;

        // 显示表单内容区域
        formContent.style.display = 'block';

        // 如果模板有关联的样品类型，自动填充
        if (template.sample_type_id) {
            sampleTypeSelect.value = template.sample_type_id;
            // 自动触发样品类型变更，加载检测项目
            await onSampleTypeChange();
        }

        // 加载模板字段配置
        const fields = await apiRequest(`/api/report-templates/${templateId}/fields`);

        // 生成模板字段表单
        if (fields && fields.length > 0) {
            let html = '<div class="row">';
            fields.forEach((field, index) => {
                const requiredMark = field.is_required ? '<span class="text-danger">*</span>' : '';
                const placeholder = field.placeholder || '';
                const defaultValue = field.default_value || '';
                const fieldType = field.field_type || 'text';

                // 根据字段类型选择输入控件
                let inputHtml = '';
                if (fieldType === 'textarea') {
                    inputHtml = `<textarea class="form-control" id="field_${field.id}"
                                    placeholder="${placeholder}" ${field.is_required ? 'required' : ''}>${defaultValue}</textarea>`;
                } else if (fieldType === 'date') {
                    inputHtml = `<input type="date" class="form-control" id="field_${field.id}"
                                    value="${defaultValue}" ${field.is_required ? 'required' : ''}>`;
                } else if (fieldType === 'number') {
                    inputHtml = `<input type="number" class="form-control" id="field_${field.id}"
                                    placeholder="${placeholder}" value="${defaultValue}" ${field.is_required ? 'required' : ''}>`;
                } else {
                    inputHtml = `<input type="text" class="form-control" id="field_${field.id}"
                                    placeholder="${placeholder}" value="${defaultValue}" ${field.is_required ? 'required' : ''}>`;
                }

                html += `
                    <div class="col-md-4 mb-3">
                        <label class="form-label">
                            ${field.field_display_name || field.field_name} ${requiredMark}
                            ${field.description ? `<i class="bi bi-info-circle text-muted" title="${field.description}"></i>` : ''}
                        </label>
                        ${inputHtml}
                        ${field.sheet_name ? `<div class="form-text">${field.sheet_name}:${field.cell_address}</div>` : ''}
                    </div>
                `;
            });
            html += '</div>';
            templateFieldsArea.innerHTML = html;
        } else {
            templateFieldsArea.innerHTML = '<p class="text-muted">该模板没有配置待填字段</p>';
        }

        showToast('模板加载成功', 'success');
    } catch (error) {
        console.error('加载模板失败:', error);
        showToast('加载模板失败: ' + error.message, 'error');
        formContent.style.display = 'none';
    }
}

// 显示导入报告基本信息模态框
function showImportReportInfoModal() {
    const modalHTML = `
        <div class="modal fade" id="importReportInfoModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-success text-white">
                        <h5 class="modal-title"><i class="bi bi-file-earmark-arrow-up"></i> 导入报告基本信息</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">选择Excel文件</label>
                            <input type="file" class="form-control" id="reportInfoFile" accept=".xlsx,.xls">
                        </div>
                        <div class="alert alert-info">
                            <small>
                                <strong>使用说明：</strong><br>
                                1. 在【报告模板管理】页面选择报告模板，点击"导出填写模板"<br>
                                2. 在导出的Excel中填写各样品的基本信息<br>
                                3. 上传填写好的Excel文件进行导入<br>
                                4. 系统将自动创建报告记录
                            </small>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-success" onclick="importReportInfo()">
                            <i class="bi bi-upload"></i> 开始导入
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    const modalContainer = document.getElementById('modalContainer');
    modalContainer.innerHTML = modalHTML;

    const modal = new bootstrap.Modal(document.getElementById('importReportInfoModal'));
    modal.show();
}

// 显示导入检测数据模态框
function showImportDetectionDataModal() {
    const modalHTML = `
        <div class="modal fade" id="importDetectionDataModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title"><i class="bi bi-clipboard-data"></i> 导入检测项目数据</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">选择Excel文件</label>
                            <input type="file" class="form-control" id="detectionDataFile" accept=".xlsx,.xls">
                        </div>
                        <div class="alert alert-warning">
                            <small>
                                <strong>使用说明：</strong><br>
                                1. 在【样品类型管理】页面选择样品类型，点击导出检测模板按钮<br>
                                2. 在导出的Excel中填写各样品的检测结果<br>
                                3. 上传填写好的Excel文件进行导入<br>
                                4. 系统将根据样品编号匹配并更新检测数据
                            </small>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-warning" onclick="importDetectionData()">
                            <i class="bi bi-upload"></i> 开始导入
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    const modalContainer = document.getElementById('modalContainer');
    modalContainer.innerHTML = modalHTML;

    const modal = new bootstrap.Modal(document.getElementById('importDetectionDataModal'));
    modal.show();
}

// 导入报告基本信息
async function importReportInfo() {
    const fileInput = document.getElementById('reportInfoFile');
    const file = fileInput.files[0];

    if (!file) {
        showToast('请选择Excel文件', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/import-report-info', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || '导入失败');
        }

        showToast(`导入成功！共创建 ${result.created_count} 份报告`, 'success');

        // 关闭模态框
        bootstrap.Modal.getInstance(document.getElementById('importReportInfoModal')).hide();

        // 刷新相关数据
        await Promise.all([
            loadPendingReports(),
            loadCompanies(),
            loadReportTemplates()
        ]);
    } catch (error) {
        showToast('导入失败: ' + error.message, 'error');
    }
}

// 导入检测项目数据
async function importDetectionData() {
    const fileInput = document.getElementById('detectionDataFile');
    const file = fileInput.files[0];

    if (!file) {
        showToast('请选择Excel文件', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/import-detection-data', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || '导入失败');
        }

        showToast(`导入成功！共更新 ${result.updated_count} 份报告的检测数据`, 'success');

        // 关闭模态框
        bootstrap.Modal.getInstance(document.getElementById('importDetectionDataModal')).hide();

        // 刷新相关数据
        await Promise.all([
            loadPendingReports(),
            loadIndicators(),
            loadSampleTypes()
        ]);
    } catch (error) {
        showToast('导入失败: ' + error.message, 'error');
    }
}

async function onSampleTypeChange() {
    const sampleTypeId = document.getElementById('reportSampleType').value;

    if (!sampleTypeId) {
        document.getElementById('reportDataArea').innerHTML = '<p class="text-muted">请先选择样品类型</p>';
        return;
    }

    try {
        const data = await apiRequest(`/api/template-indicators?sample_type_id=${sampleTypeId}`);

        if (data.length === 0) {
            document.getElementById('reportDataArea').innerHTML = '<p class="text-warning">该样品类型未配置检测项目，请先在模板管理中配置</p>';
            return;
        }

        // 按分组组织数据
        const groups = {};
        data.forEach(item => {
            const groupName = item.group_name || '其他';
            if (!groups[groupName]) groups[groupName] = [];
            groups[groupName].push(item);
        });

        let html = '';
        for (const [groupName, items] of Object.entries(groups)) {
            html += `<div class="indicator-group-header">${groupName}</div>`;
            html += '<div class="indicator-input-group">';

            items.forEach(item => {
                html += `
                    <div class="indicator-row">
                        <div class="indicator-label">${item.indicator_name}</div>
                        <input type="text" class="form-control indicator-input"
                               data-indicator-id="${item.indicator_id}"
                               placeholder="请输入检测值"
                               value="${item.default_value || ''}">
                        <div class="indicator-unit">${item.unit || ''}</div>
                    </div>
                `;
            });

            html += '</div>';
        }

        document.getElementById('reportDataArea').innerHTML = html;
    } catch (error) {
        console.error('加载检测项目失败:', error);
    }
}

async function submitReport(e) {
    e.preventDefault();
    await saveOrSubmitReport('pending');
}

async function saveDraft() {
    await saveOrSubmitReport('draft');
}

async function saveOrSubmitReport(reviewStatus) {
    const sampleNumber = document.getElementById('sampleNumber').value;
    const sampleTypeId = document.getElementById('reportSampleType').value;
    const companyId = document.getElementById('reportCompany').value || null;
    const detectionDate = document.getElementById('detectionDate').value;
    const detectionPerson = document.getElementById('detectionPerson').value;
    const reviewPerson = document.getElementById('reviewPerson').value;
    const remark = document.getElementById('reportRemark').value;
    const templateId = document.getElementById('reportTemplate').value;

    // 收集检测数据
    const dataInputs = document.querySelectorAll('.indicator-input');
    const data = [];
    dataInputs.forEach(input => {
        const indicatorId = input.getAttribute('data-indicator-id');
        const measuredValue = input.value.trim();
        if (measuredValue) {
            data.push({
                indicator_id: parseInt(indicatorId),
                measured_value: measuredValue,
                remark: ''
            });
        }
    });

    // 收集模板字段值
    const templateFields = [];
    document.querySelectorAll('[id^="field_"]').forEach(input => {
        const fieldMappingId = input.id.replace('field_', '');
        const fieldValue = input.value.trim();
        if (fieldValue) {
            templateFields.push({
                field_mapping_id: parseInt(fieldMappingId),
                field_value: fieldValue
            });
        }
    });

    try {
        let result;

        // 检测是否为编辑模式
        if (AppState.editingReportId) {
            // 更新现有报告
            result = await apiRequest(`/api/reports/${AppState.editingReportId}`, {
                method: 'PUT',
                body: JSON.stringify({
                    company_id: companyId ? parseInt(companyId) : null,
                    detection_date: detectionDate,
                    detection_person: detectionPerson,
                    review_person: reviewPerson,
                    remark: remark,
                    template_fields: templateFields,
                    data: data
                })
            });

            showToast('报告更新成功！');

            // 清除编辑状态
            AppState.editingReportId = null;

            // 恢复按钮文本
            const submitBtn = document.querySelector('#reportForm button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<i class="bi bi-check-circle"></i> 提交审核';
            }
            const draftBtn = document.getElementById('saveDraftBtn');
            if (draftBtn) {
                draftBtn.innerHTML = '<i class="bi bi-save"></i> 保存草稿';
            }

        } else {
            // 创建新报告
            result = await apiRequest('/api/reports', {
                method: 'POST',
                body: JSON.stringify({
                    sample_number: sampleNumber,
                    sample_type_id: parseInt(sampleTypeId),
                    company_id: companyId ? parseInt(companyId) : null,
                    detection_date: detectionDate,
                    detection_person: detectionPerson,
                    review_person: reviewPerson,
                    remark: remark,
                    template_id: templateId ? parseInt(templateId) : null,
                    template_fields: templateFields,
                    data: data,
                    review_status: reviewStatus
                })
            });

            const statusText = reviewStatus === 'draft' ? '保存草稿' : '提交审核';
            showToast(`${statusText}成功！报告编号: ${result.report_number}`);
        }

        // 重置表单
        document.getElementById('reportForm').reset();
        document.getElementById('reportDataArea').innerHTML = '<p class="text-muted">请先选择样品类型</p>';
        document.getElementById('reportFormContent').style.display = 'none';
        document.getElementById('templateFieldsArea').innerHTML = '';

        // 刷新待提交报告列表
        loadPendingReports();

    } catch (error) {
        console.error('操作失败:', error);
    }
}

async function exportReportTemplate() {
    const sampleTypeId = document.getElementById('reportSampleType').value;
    if (!sampleTypeId) {
        showToast('请先选择样品类型', 'warning');
        return;
    }

    try {
        const response = await fetch(`/api/reports/export/template?sample_type_id=${sampleTypeId}`);
        if (!response.ok) throw new Error('导出失败');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `报告导入模板_${Date.now()}.xlsx`;
        a.click();

        showToast('模板导出成功');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

function showImportReportsModal() {
    const modalHTML = `
        <div class="modal fade" id="importReportsModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">批量导入报告</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">选择Excel文件</label>
                            <input type="file" class="form-control" id="reportsFile" accept=".xlsx,.xls">
                        </div>
                        <div class="alert alert-info">
                            <small>
                                <strong>使用说明：</strong><br>
                                1. 先在报告填写页面选择样品类型，然后点击"下载模板"获取导入模板<br>
                                2. 在模板中填写报告数据<br>
                                3. 上传填好的Excel文件进行批量导入
                            </small>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="importReportsExcel()">导入</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('modalContainer').innerHTML = modalHTML;
    const modal = new bootstrap.Modal(document.getElementById('importReportsModal'));
    modal.show();
}

// ==================== 新建报告流程（新版本） ====================
// 流程状态
const NewReportState = {
    selectedTemplateId: null,
    templateExcelFile: null,
    templateExcelData: null,
    selectedSampleTypeId: null,
    detectionExcelFile: null,
    detectionExcelData: null,
    parsedData: null
};

// 步骤1: 选择报告模板
function onNewReportTemplateChange() {
    const templateId = document.getElementById('reportTemplate').value;
    const downloadBtn = document.getElementById('downloadTemplateExcelBtn');
    const fileInput = document.getElementById('templateExcelFile');
    const step1Status = document.getElementById('step1Status');

    if (templateId) {
        NewReportState.selectedTemplateId = templateId;
        downloadBtn.disabled = false;
        fileInput.disabled = false;
        step1Status.innerHTML = '<small class="text-success"><i class="bi bi-check-circle"></i> 已选择模板，请下载并填写Excel模板</small>';
    } else {
        NewReportState.selectedTemplateId = null;
        downloadBtn.disabled = true;
        fileInput.disabled = true;
        fileInput.value = '';
        step1Status.innerHTML = '<small class="text-muted">请先选择报告模板</small>';

        // 重置步骤2和3
        resetStep2();
        resetStep3();
    }
}

// 下载报告模板Excel
async function downloadTemplateExcel() {
    if (!NewReportState.selectedTemplateId) {
        showToast('请先选择报告模板', 'warning');
        return;
    }

    try {
        const response = await fetch(`/api/export-report-template/${NewReportState.selectedTemplateId}`);
        if (!response.ok) throw new Error('下载失败');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `报告模板_${Date.now()}.xlsx`;
        a.click();

        showToast('模板下载成功，请填写后上传', 'success');
    } catch (error) {
        showToast('下载失败: ' + error.message, 'error');
    }
}

// 上传报告模板Excel
function onTemplateExcelUploaded(event) {
    const file = event.target.files[0];
    const step1Status = document.getElementById('step1Status');
    const step2Card = document.getElementById('step2Card');
    const sampleTypeSelect = document.getElementById('reportSampleType');

    if (file) {
        NewReportState.templateExcelFile = file;
        step1Status.innerHTML = `<small class="text-success"><i class="bi bi-check-circle-fill"></i> 已上传: ${file.name}</small>`;

        // 启用步骤2
        step2Card.style.opacity = '1';
        step2Card.style.pointerEvents = 'auto';
        sampleTypeSelect.disabled = false;
        sampleTypeSelect.innerHTML = '<option value="">请选择样品类型...</option>';

        // 加载样品类型列表
        AppState.sampleTypes.forEach(st => {
            const option = document.createElement('option');
            option.value = st.id;
            option.textContent = st.name;
            sampleTypeSelect.appendChild(option);
        });

        document.getElementById('step2Status').innerHTML = '<small class="text-primary">请选择样品类型</small>';
    } else {
        NewReportState.templateExcelFile = null;
        step1Status.innerHTML = '<small class="text-warning">请上传填写好的Excel</small>';
        resetStep2();
    }
}

// 步骤2: 选择样品类型
function onNewSampleTypeChange() {
    const sampleTypeId = document.getElementById('reportSampleType').value;
    const downloadBtn = document.getElementById('downloadDetectionExcelBtn');
    const fileInput = document.getElementById('detectionExcelFile');
    const step2Status = document.getElementById('step2Status');

    if (sampleTypeId) {
        NewReportState.selectedSampleTypeId = sampleTypeId;
        downloadBtn.disabled = false;
        fileInput.disabled = false;
        step2Status.innerHTML = '<small class="text-success"><i class="bi bi-check-circle"></i> 已选择样品类型，请下载并填写检测数据Excel</small>';
    } else {
        NewReportState.selectedSampleTypeId = null;
        downloadBtn.disabled = true;
        fileInput.disabled = true;
        fileInput.value = '';
        step2Status.innerHTML = '<small class="text-muted">请选择样品类型</small>';
        resetStep3();
    }
}

// 下载检测数据Excel
async function downloadDetectionExcel() {
    if (!NewReportState.selectedSampleTypeId) {
        showToast('请先选择样品类型', 'warning');
        return;
    }

    try {
        const response = await fetch(`/api/export-sample-type-template/${NewReportState.selectedSampleTypeId}`);
        if (!response.ok) throw new Error('下载失败');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `检测数据模板_${Date.now()}.xlsx`;
        a.click();

        showToast('模板下载成功，请填写后上传', 'success');
    } catch (error) {
        showToast('下载失败: ' + error.message, 'error');
    }
}

// 上传检测数据Excel
function onDetectionExcelUploaded(event) {
    const file = event.target.files[0];
    const step2Status = document.getElementById('step2Status');
    const step3Card = document.getElementById('step3Card');
    const parseBtn = document.getElementById('parseAndPreviewBtn');

    if (file) {
        NewReportState.detectionExcelFile = file;
        step2Status.innerHTML = `<small class="text-success"><i class="bi bi-check-circle-fill"></i> 已上传: ${file.name}</small>`;

        // 启用步骤3
        step3Card.style.opacity = '1';
        step3Card.style.pointerEvents = 'auto';
        parseBtn.disabled = false;
        document.getElementById('step3Status').innerHTML = '<small class="text-primary">可以开始解析数据了</small>';
    } else {
        NewReportState.detectionExcelFile = null;
        step2Status.innerHTML = '<small class="text-warning">请上传填写好的Excel</small>';
        resetStep3();
    }
}

// 解析Excel并生成预览
async function parseAndPreview() {
    if (!NewReportState.templateExcelFile || !NewReportState.detectionExcelFile) {
        showToast('请先上传报告模板和检测数据Excel', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('template_id', NewReportState.selectedTemplateId);
    formData.append('sample_type_id', NewReportState.selectedSampleTypeId);
    formData.append('template_excel', NewReportState.templateExcelFile);
    formData.append('detection_excel', NewReportState.detectionExcelFile);

    try {
        // 步骤1: 验证Excel文件
        document.getElementById('step3Status').innerHTML = '<small class="text-info"><i class="bi bi-hourglass-split"></i> 正在验证Excel文件格式...</small>';

        const validateResponse = await fetch('/api/validate-report-excel', {
            method: 'POST',
            body: formData
        });

        const validateResult = await validateResponse.json();

        if (!validateResponse.ok || !validateResult.valid) {
            // 验证失败，显示错误信息
            let errorMsg = '<div class="alert alert-danger"><strong>Excel文件验证失败！</strong><br><br>';

            if (validateResult.errors && validateResult.errors.length > 0) {
                errorMsg += '<strong>错误：</strong><ul>';
                validateResult.errors.forEach(err => {
                    errorMsg += `<li>${err}</li>`;
                });
                errorMsg += '</ul>';
            }

            if (validateResult.warnings && validateResult.warnings.length > 0) {
                errorMsg += '<strong>警告：</strong><ul>';
                validateResult.warnings.forEach(warn => {
                    errorMsg += `<li>${warn}</li>`;
                });
                errorMsg += '</ul>';
            }

            errorMsg += '</div>';

            document.getElementById('step3Status').innerHTML = '<small class="text-danger"><i class="bi bi-x-circle"></i> 验证失败</small>';

            // 使用模态框显示详细错误
            showValidationErrorModal(errorMsg);
            return;
        }

        // 如果有警告，显示但继续
        if (validateResult.warnings && validateResult.warnings.length > 0) {
            let warnMsg = '发现以下警告，但可以继续：\n\n';
            validateResult.warnings.forEach(warn => {
                warnMsg += `• ${warn}\n`;
            });

            if (!confirm(warnMsg + '\n是否继续解析？')) {
                document.getElementById('step3Status').innerHTML = '<small class="text-warning"><i class="bi bi-exclamation-triangle"></i> 已取消</small>';
                return;
            }
        }

        // 步骤2: 解析Excel数据
        document.getElementById('step3Status').innerHTML = '<small class="text-info"><i class="bi bi-hourglass-split"></i> 正在解析Excel数据...</small>';

        const parseResponse = await fetch('/api/parse-report-excel', {
            method: 'POST',
            body: formData
        });

        const parseResult = await parseResponse.json();

        if (!parseResponse.ok) {
            throw new Error(parseResult.error || '解析失败');
        }

        NewReportState.parsedData = parseResult;

        // 显示预览区域
        renderPreviewData(parseResult);

        document.getElementById('step3Status').innerHTML = '<small class="text-success"><i class="bi bi-check-circle-fill"></i> 解析成功！</small>';
        showToast('Excel数据解析成功，请查看预览并编辑', 'success');

        // 滚动到预览区域
        document.getElementById('dataPreviewArea').scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        document.getElementById('step3Status').innerHTML = '<small class="text-danger"><i class="bi bi-x-circle"></i> 解析失败</small>';
        showToast('解析失败: ' + error.message, 'error');
    }
}

// 显示验证错误模态框
function showValidationErrorModal(errorHtml) {
    const modalHTML = `
        <div class="modal fade" id="validationErrorModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header bg-danger text-white">
                        <h5 class="modal-title"><i class="bi bi-exclamation-triangle-fill"></i> Excel文件验证失败</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        ${errorHtml}
                        <div class="mt-3">
                            <strong>建议：</strong>
                            <ul>
                                <li>检查上传的Excel文件是否是从系统下载的模板</li>
                                <li>确保Excel文件格式正确，没有删除或修改关键列</li>
                                <li>确保所有必填字段都已填写</li>
                            </ul>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('modalContainer').innerHTML = modalHTML;
    const modal = new bootstrap.Modal(document.getElementById('validationErrorModal'));
    modal.show();
}

// 渲染预览数据
function renderPreviewData(data) {
    const previewArea = document.getElementById('dataPreviewArea');
    previewArea.style.display = 'block';

    // 渲染基本信息
    const basicInfoArea = document.getElementById('basicInfoArea');
    let basicHtml = '<div class="row">';

    const basicFields = [
        { key: 'sample_number', label: '样品编号', required: true },
        { key: 'company_name', label: '委托单位', required: false },
        { key: 'detection_date', label: '检测日期', type: 'date', required: false },
        { key: 'detection_person', label: '检测人员', required: false },
        { key: 'review_person', label: '审核人员', required: false },
        { key: 'remark', label: '备注', required: false }
    ];

    basicFields.forEach(field => {
        const value = data.basic_info ? data.basic_info[field.key] || '' : '';
        const type = field.type || 'text';
        const required = field.required ? 'required' : '';
        const requiredMark = field.required ? '<span class="text-danger">*</span>' : '';

        basicHtml += `
            <div class="col-md-4 mb-3">
                <label class="form-label">${field.label} ${requiredMark}</label>
                <input type="${type}" class="form-control" id="preview_${field.key}" value="${value}" ${required}>
            </div>
        `;
    });

    basicHtml += '</div>';
    basicInfoArea.innerHTML = basicHtml;

    // 渲染模板字段
    const templateFieldsArea = document.getElementById('templateFieldsPreviewArea');
    if (data.template_fields && data.template_fields.length > 0) {
        let fieldsHtml = '<div class="row">';
        data.template_fields.forEach(field => {
            const requiredMark = field.is_required ? '<span class="text-danger">*</span>' : '';
            const required = field.is_required ? 'required' : '';
            const type = field.field_type === 'date' ? 'date' : field.field_type === 'number' ? 'number' : 'text';

            fieldsHtml += `
                <div class="col-md-4 mb-3">
                    <label class="form-label">${field.field_name} ${requiredMark}</label>
                    <input type="${type}" class="form-control" id="preview_field_${field.field_mapping_id}"
                           value="${field.field_value || ''}" ${required}>
                </div>
            `;
        });
        fieldsHtml += '</div>';
        templateFieldsArea.innerHTML = fieldsHtml;
    } else {
        templateFieldsArea.innerHTML = '<p class="text-muted">无模板字段</p>';
    }

    // 渲染检测数据
    const detectionDataArea = document.getElementById('detectionDataPreviewArea');
    if (data.detection_data && data.detection_data.length > 0) {
        // 按分组组织数据
        const groups = {};
        data.detection_data.forEach(item => {
            const groupName = item.group_name || '其他';
            if (!groups[groupName]) groups[groupName] = [];
            groups[groupName].push(item);
        });

        let dataHtml = '';
        for (const [groupName, items] of Object.entries(groups)) {
            dataHtml += `<div class="mb-3"><h6 class="border-bottom pb-2">${groupName}</h6><div class="row">`;

            items.forEach(item => {
                dataHtml += `
                    <div class="col-md-3 mb-3">
                        <label class="form-label">${item.indicator_name}</label>
                        <div class="input-group input-group-sm">
                            <input type="text" class="form-control" id="preview_indicator_${item.indicator_id}"
                                   value="${item.measured_value || ''}" placeholder="检测值">
                            <span class="input-group-text">${item.unit || ''}</span>
                        </div>
                        ${item.limit_value ? `<small class="text-muted">限值: ${item.limit_value}</small>` : ''}
                    </div>
                `;
            });

            dataHtml += '</div></div>';
        }
        detectionDataArea.innerHTML = dataHtml;
    } else {
        detectionDataArea.innerHTML = '<p class="text-muted">无检测数据</p>';
    }
}

// 从预览保存草稿
async function saveDraftFromPreview() {
    await submitReportFromPreview('draft');
}

// 从预览提交报告
async function submitReportFromPreview(reviewStatus = 'pending') {
    try {
        // 查找公司ID
        const companyName = document.getElementById('preview_company_name').value;
        let companyId = null;

        if (companyName) {
            const company = AppState.companies.find(c => c.name === companyName);
            if (company) {
                companyId = company.id;
            }
        }

        // 收集数据
        const reportData = {
            template_id: parseInt(NewReportState.selectedTemplateId),
            sample_type_id: parseInt(NewReportState.selectedSampleTypeId),
            sample_number: document.getElementById('preview_sample_number').value,
            company_id: companyId,
            detection_date: document.getElementById('preview_detection_date').value || null,
            detection_person: document.getElementById('preview_detection_person').value || null,
            review_person: document.getElementById('preview_review_person').value || null,
            remark: document.getElementById('preview_remark').value || null,
            review_status: reviewStatus,
            template_fields: [],
            data: []  // 后端期望的字段名是 'data'，不是 'detection_data'
        };

        // 收集模板字段
        document.querySelectorAll('[id^="preview_field_"]').forEach(input => {
            const fieldMappingId = input.id.replace('preview_field_', '');
            if (input.value) {
                reportData.template_fields.push({
                    field_mapping_id: parseInt(fieldMappingId),
                    field_value: input.value
                });
            }
        });

        // 收集检测数据
        document.querySelectorAll('[id^="preview_indicator_"]').forEach(input => {
            const indicatorId = input.id.replace('preview_indicator_', '');
            const value = input.value.trim();
            if (value) {
                reportData.data.push({
                    indicator_id: parseInt(indicatorId),
                    measured_value: value,
                    remark: ''
                });
            }
        });

        const response = await fetch('/api/reports', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(reportData)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || '提交失败');
        }

        const statusText = reviewStatus === 'draft' ? '草稿保存' : '报告提交';
        showToast(`${statusText}成功！报告编号: ${result.report_number}`, 'success');

        // 刷新列表并重置表单
        await loadPendingReports();
        resetNewReportForm();

    } catch (error) {
        showToast('操作失败: ' + error.message, 'error');
    }
}

// 直接生成报告
async function generateReportDirect() {
    if (!confirm('确定要直接生成报告吗？生成后将无法修改。')) {
        return;
    }

    try {
        // 先提交报告
        await submitReportFromPreview('approved');

        // TODO: 调用生成报告的API
        showToast('报告已生成，请在报告生成页面查看', 'success');

    } catch (error) {
        showToast('生成报告失败: ' + error.message, 'error');
    }
}

// 重置表单
function resetNewReportForm() {
    // 重置状态
    NewReportState.selectedTemplateId = null;
    NewReportState.templateExcelFile = null;
    NewReportState.selectedSampleTypeId = null;
    NewReportState.detectionExcelFile = null;
    NewReportState.parsedData = null;

    // 重置UI
    document.getElementById('reportTemplate').value = '';
    document.getElementById('templateExcelFile').value = '';
    document.getElementById('reportSampleType').value = '';
    document.getElementById('detectionExcelFile').value = '';

    resetStep1();
    resetStep2();
    resetStep3();

    document.getElementById('dataPreviewArea').style.display = 'none';
}

function resetStep1() {
    document.getElementById('downloadTemplateExcelBtn').disabled = true;
    document.getElementById('templateExcelFile').disabled = true;
    document.getElementById('templateExcelFile').value = '';
    document.getElementById('step1Status').innerHTML = '<small class="text-muted">请先选择报告模板</small>';
}

function resetStep2() {
    const step2Card = document.getElementById('step2Card');
    step2Card.style.opacity = '0.6';
    step2Card.style.pointerEvents = 'none';

    document.getElementById('reportSampleType').disabled = true;
    document.getElementById('reportSampleType').value = '';
    document.getElementById('downloadDetectionExcelBtn').disabled = true;
    document.getElementById('detectionExcelFile').disabled = true;
    document.getElementById('detectionExcelFile').value = '';
    document.getElementById('step2Status').innerHTML = '<small class="text-muted">请先完成步骤1</small>';
}

function resetStep3() {
    const step3Card = document.getElementById('step3Card');
    step3Card.style.opacity = '0.6';
    step3Card.style.pointerEvents = 'none';

    document.getElementById('parseAndPreviewBtn').disabled = true;
    document.getElementById('step3Status').innerHTML = '<small class="text-muted">请先完成步骤1和步骤2</small>';
}

async function importReportsExcel() {
    const fileInput = document.getElementById('reportsFile');
    const file = fileInput.files[0];

    if (!file) {
        showToast('请选择文件', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/reports/import/excel', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || '导入失败');
        }

        let message = data.message;
        if (data.errors && data.errors.length > 0) {
            message += '\n\n错误信息：\n' + data.errors.join('\n');
        }

        showToast(message);
        bootstrap.Modal.getInstance(document.getElementById('importReportsModal')).hide();
        await loadReports();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ==================== 报告查询 ====================
async function loadReports(searchParams = {}) {
    try {
        const params = new URLSearchParams(searchParams);
        const data = await apiRequest(`/api/reports?${params}`);
        AppState.reports = data;
        updateReportsList();
    } catch (error) {
        console.error('加载报告列表失败:', error);
    }
}

function updateReportsList() {
    const tbody = document.getElementById('reportsList');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (AppState.reports.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">暂无数据</td></tr>';
        return;
    }

    AppState.reports.forEach(report => {
        tbody.innerHTML += `
            <tr onclick="viewReport(${report.id})" style="cursor:pointer;">
                <td>${report.report_number}</td>
                <td>${report.sample_number}</td>
                <td>${report.sample_type_name || '-'}</td>
                <td>${report.company_name || '-'}</td>
                <td>${report.detection_date || '-'}</td>
                <td>${formatDateTime(report.created_at)}</td>
                <td onclick="event.stopPropagation();">
                    <button class="btn btn-sm btn-primary me-1" onclick="viewReport(${report.id})">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-warning me-1" onclick="showEditReportModal(${report.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-success me-1" onclick="exportReport(${report.id}, 'excel')">
                        <i class="bi bi-file-earmark-excel"></i>
                    </button>
                    <button class="btn btn-sm btn-info me-1" onclick="exportReport(${report.id}, 'word')">
                        <i class="bi bi-file-earmark-word"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteReport(${report.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });
}

function searchReports() {
    const sampleNumber = document.getElementById('searchSampleNumber').value;
    const companyId = document.getElementById('searchCompany').value;

    const searchParams = {};
    if (sampleNumber) searchParams.sample_number = sampleNumber;
    if (companyId) searchParams.company_id = companyId;

    loadReports(searchParams);
}

async function viewReport(id) {
    try {
        const report = await apiRequest(`/api/reports/${id}`);

        // 按分组组织数据
        const groups = {};
        report.data.forEach(item => {
            const groupName = item.group_name || '其他';
            if (!groups[groupName]) groups[groupName] = [];
            groups[groupName].push(item);
        });

        let dataHTML = '';
        for (const [groupName, items] of Object.entries(groups)) {
            dataHTML += `
                <h6 class="mt-3">${groupName}</h6>
                <table class="table table-bordered table-sm">
                    <thead>
                        <tr>
                            <th>检测项目</th>
                            <th>单位</th>
                            <th>检测值</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            items.forEach(item => {
                dataHTML += `
                    <tr>
                        <td>${item.indicator_name}</td>
                        <td>${item.unit || '-'}</td>
                        <td>${item.measured_value || '-'}</td>
                    </tr>
                `;
            });

            dataHTML += '</tbody></table>';
        }

        const modalHTML = `
            <div class="modal fade" id="viewReportModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">报告详情 - ${report.report_number}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="report-detail-section">
                                <h6>基本信息</h6>
                                <div class="report-info-row">
                                    <div class="report-info-label">报告编号:</div>
                                    <div class="report-info-value">${report.report_number}</div>
                                </div>
                                <div class="report-info-row">
                                    <div class="report-info-label">样品编号:</div>
                                    <div class="report-info-value">${report.sample_number}</div>
                                </div>
                                <div class="report-info-row">
                                    <div class="report-info-label">样品类型:</div>
                                    <div class="report-info-value">${report.sample_type_name}</div>
                                </div>
                                <div class="report-info-row">
                                    <div class="report-info-label">委托单位:</div>
                                    <div class="report-info-value">${report.company_name || '-'}</div>
                                </div>
                                <div class="report-info-row">
                                    <div class="report-info-label">检测日期:</div>
                                    <div class="report-info-value">${report.detection_date || '-'}</div>
                                </div>
                                <div class="report-info-row">
                                    <div class="report-info-label">检测人员:</div>
                                    <div class="report-info-value">${report.detection_person || '-'}</div>
                                </div>
                                <div class="report-info-row">
                                    <div class="report-info-label">审核人员:</div>
                                    <div class="report-info-value">${report.review_person || '-'}</div>
                                </div>
                            </div>
                            <div class="report-detail-section">
                                <h6>检测数据</h6>
                                ${dataHTML}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.getElementById('modalContainer').innerHTML = modalHTML;
        const modal = new bootstrap.Modal(document.getElementById('viewReportModal'));
        modal.show();
    } catch (error) {
        console.error('查看报告失败:', error);
    }
}

async function showEditReportModal(id) {
    try {
        const report = await apiRequest(`/api/reports/${id}`);

        // 生成检测数据输入区域
        const groups = {};
        report.data.forEach(item => {
            const groupName = item.group_name || '其他';
            if (!groups[groupName]) groups[groupName] = [];
            groups[groupName].push(item);
        });

        let dataHTML = '';
        for (const [groupName, items] of Object.entries(groups)) {
            dataHTML += `<div class="indicator-group-header">${groupName}</div>`;
            dataHTML += '<div class="indicator-input-group">';

            items.forEach(item => {
                dataHTML += `
                    <div class="indicator-row">
                        <div class="indicator-label">${item.indicator_name}</div>
                        <input type="text" class="form-control indicator-input"
                               data-indicator-id="${item.indicator_id}"
                               value="${item.measured_value || ''}"
                               placeholder="请输入检测值">
                        <div class="indicator-unit">${item.unit || ''}</div>
                    </div>
                `;
            });

            dataHTML += '</div>';
        }

        const modalHTML = `
            <div class="modal fade" id="editReportModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">修改报告 - ${report.report_number}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="editReportForm">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label">委托单位</label>
                                            <select class="form-select" id="editReportCompany">
                                                <option value="">请选择...</option>
                                                ${AppState.companies.map(c =>
                                                    `<option value="${c.id}" ${c.id === report.company_id ? 'selected' : ''}>${c.name}</option>`
                                                ).join('')}
                                            </select>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label">检测日期</label>
                                            <input type="date" class="form-control" id="editDetectionDate" value="${report.detection_date || ''}">
                                        </div>
                                    </div>
                                </div>
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label">检测人员</label>
                                            <input type="text" class="form-control" id="editDetectionPerson" value="${report.detection_person || ''}">
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="mb-3">
                                            <label class="form-label">审核人员</label>
                                            <input type="text" class="form-control" id="editReviewPerson" value="${report.review_person || ''}">
                                        </div>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">备注</label>
                                    <input type="text" class="form-control" id="editReportRemark" value="${report.remark || ''}">
                                </div>
                                <hr>
                                <h6>检测项目数据</h6>
                                <div id="editReportDataArea">
                                    ${dataHTML}
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                            <button type="button" class="btn btn-primary" onclick="updateReport(${id})">保存</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.getElementById('modalContainer').innerHTML = modalHTML;
        const modal = new bootstrap.Modal(document.getElementById('editReportModal'));
        modal.show();
    } catch (error) {
        console.error('加载报告失败:', error);
    }
}

async function updateReport(id) {
    const companyId = document.getElementById('editReportCompany').value || null;
    const detectionDate = document.getElementById('editDetectionDate').value;
    const detectionPerson = document.getElementById('editDetectionPerson').value;
    const reviewPerson = document.getElementById('editReviewPerson').value;
    const remark = document.getElementById('editReportRemark').value;

    // 收集检测数据
    const dataInputs = document.querySelectorAll('#editReportDataArea .indicator-input');
    const data = [];
    dataInputs.forEach(input => {
        const indicatorId = input.getAttribute('data-indicator-id');
        const measuredValue = input.value.trim();
        data.push({
            indicator_id: parseInt(indicatorId),
            measured_value: measuredValue,
            remark: ''
        });
    });

    try {
        await apiRequest(`/api/reports/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
                company_id: companyId ? parseInt(companyId) : null,
                detection_date: detectionDate,
                detection_person: detectionPerson,
                review_person: reviewPerson,
                remark: remark,
                data: data
            })
        });

        showToast('报告更新成功');
        bootstrap.Modal.getInstance(document.getElementById('editReportModal')).hide();
        await loadReports();
    } catch (error) {
        console.error('更新报告失败:', error);
    }
}

async function exportReport(id, format) {
    const url = `/api/reports/${id}/export/${format}`;

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('导出失败');

        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        const extMap = { 'excel': 'xlsx', 'word': 'docx' };
        a.download = `report_${id}.${extMap[format] || format}`;
        a.click();

        showToast('报告导出成功');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function deleteReport(id) {
    if (!confirm('确定要删除这个报告吗？删除后无法恢复！')) return;

    try {
        await apiRequest(`/api/reports/${id}`, { method: 'DELETE' });
        showToast('报告删除成功');
        await loadReports();
    } catch (error) {
        console.error('删除报告失败:', error);
    }
}

// ==================== 数据管理 ====================
async function createBackup() {
    try {
        const data = await apiRequest('/api/backup/create', { method: 'POST' });
        showToast(data.message);
        await loadBackups();
    } catch (error) {
        console.error('创建备份失败:', error);
    }
}

async function loadBackups() {
    try {
        const data = await apiRequest('/api/backup/list');
        updateBackupsList(data);
    } catch (error) {
        console.error('加载备份列表失败:', error);
    }
}

function updateBackupsList(backups) {
    const tbody = document.getElementById('backupsList');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (backups.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无备份</td></tr>';
        return;
    }

    backups.forEach(backup => {
        tbody.innerHTML += `
            <tr>
                <td>${backup.name}</td>
                <td><small class="text-muted">${backup.description || '-'}</small></td>
                <td>${formatDateTime(backup.backup_time)}</td>
                <td>
                    <button class="btn btn-sm btn-primary me-1" onclick="downloadBackup('${backup.name}')">
                        <i class="bi bi-download"></i> 下载
                    </button>
                    <button class="btn btn-sm btn-warning me-1" onclick="restoreBackup('${backup.name}')">
                        <i class="bi bi-arrow-counterclockwise"></i> 恢复
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteBackup('${backup.name}')">
                        <i class="bi bi-trash"></i> 删除
                    </button>
                </td>
            </tr>
        `;
    });
}

function downloadBackup(backupName) {
    window.location.href = '/api/backup/download/' + encodeURIComponent(backupName);
}

async function importBackup(input) {
    const file = input.files[0];
    if (!file) return;
    input.value = '';

    if (!file.name.endsWith('.db')) {
        showToast('仅支持 .db 格式的SQLite数据库文件', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/backup/import', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (response.ok) {
            showToast(data.message);
            await loadBackups();
        } else {
            showToast(data.error || '导入失败', 'error');
        }
    } catch (error) {
        console.error('导入备份失败:', error);
        showToast('导入备份失败', 'error');
    }
}

async function deleteBackup(backupName) {
    if (!confirm('⚠️ 确定要删除备份 "' + backupName + '" 吗？\n\n删除后将无法恢复，请确认该备份不再需要！')) return;
    if (!confirm('⚠️ 再次确认：删除备份 "' + backupName + '"？\n此操作不可撤销！')) return;
    try {
        const data = await apiRequest('/api/backup/delete/' + encodeURIComponent(backupName), { method: 'DELETE' });
        showToast(data.message);
        await loadBackups();
    } catch (error) {
        console.error('删除备份失败:', error);
    }
}

async function restoreBackup(backupName) {
    if (!confirm('确定要恢复此备份吗？当前数据将被覆盖！')) return;

    try {
        await apiRequest('/api/backup/restore', {
            method: 'POST',
            body: JSON.stringify({ backup_name: backupName })
        });

        showToast('备份恢复成功，页面将刷新');
        setTimeout(() => location.reload(), 2000);
    } catch (error) {
        console.error('恢复备份失败:', error);
    }
}

async function loadLogs() {
    try {
        const data = await apiRequest('/api/logs?limit=50');
        updateLogsList(data);
    } catch (error) {
        console.error('加载日志失败:', error);
    }
}

function updateLogsList(logs) {
    const tbody = document.getElementById('logsList');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无日志</td></tr>';
        return;
    }

    logs.forEach(log => {
        tbody.innerHTML += `
            <tr>
                <td>${formatDateTime(log.created_at)}</td>
                <td>${log.username || '-'}</td>
                <td>${log.operation_type}</td>
                <td>${log.operation_detail || '-'}</td>
            </tr>
        `;
    });
}

async function loadUsers() {
    try {
        const data = await apiRequest('/api/users');
        updateUsersList(data);
    } catch (error) {
        console.error('加载用户列表失败:', error);
    }
}

function updateUsersList(users) {
    const tbody = document.getElementById('usersList');
    if (!tbody) return;

    tbody.innerHTML = '';

    users.forEach(user => {
        const roleBadge = user.role === 'admin'
            ? '<span class="badge bg-danger">管理员</span>'
            : '<span class="badge bg-primary">填写人</span>';

        tbody.innerHTML += `
            <tr>
                <td>${user.username}</td>
                <td>${roleBadge}</td>
                <td>${formatDateTime(user.created_at)}</td>
            </tr>
        `;
    });
}

function showAddUserModal() {
    const modalHTML = `
        <div class="modal fade" id="addUserModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">添加用户</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="addUserForm">
                            <div class="mb-3">
                                <label class="form-label">用户名 <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="newUsername" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">密码 <span class="text-danger">*</span></label>
                                <input type="password" class="form-control" id="newPassword" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">角色</label>
                                <select class="form-select" id="newUserRole">
                                    <option value="reporter">填写人</option>
                                    <option value="admin">管理员</option>
                                </select>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="addUser()">保存</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('modalContainer').innerHTML = modalHTML;
    const modal = new bootstrap.Modal(document.getElementById('addUserModal'));
    modal.show();
}

async function addUser() {
    const username = document.getElementById('newUsername').value;
    const password = document.getElementById('newPassword').value;
    const role = document.getElementById('newUserRole').value;

    try {
        await apiRequest('/api/users', {
            method: 'POST',
            body: JSON.stringify({ username, password, role })
        });

        showToast('用户添加成功');
        bootstrap.Modal.getInstance(document.getElementById('addUserModal')).hide();
        await loadUsers();
    } catch (error) {
        console.error('添加用户失败:', error);
    }
}

// ==================== 待提交报告 ====================

async function loadPendingReports() {
    try {
        const sampleNumber = document.getElementById('pendingSearchSampleNumber').value;
        const companyId = document.getElementById('pendingSearchCompany').value;

        let url = '/api/reports/pending-submit?';
        if (sampleNumber) url += `sample_number=${sampleNumber}&`;
        if (companyId) url += `company_id=${companyId}&`;

        const reports = await apiRequest(url);

        const tbody = document.getElementById('pendingReportsTableBody');

        if (reports.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">暂无待提交报告</td></tr>';
            return;
        }

        tbody.innerHTML = reports.map(report => {
            const statusBadge = report.review_status === 'draft'
                ? '<span class="badge bg-secondary">草稿</span>'
                : '<span class="badge bg-danger">已拒绝</span>';

            const rejectReason = report.review_status === 'rejected' && report.review_comment
                ? report.review_comment
                : '-';

            // 解析客户信息
            let customerUnit = '-';
            let customerPlant = '-';
            try {
                if (report.remark) {
                    const customerInfo = JSON.parse(report.remark);
                    customerUnit = customerInfo.customer_unit || '-';
                    customerPlant = customerInfo.customer_plant || '-';
                }
            } catch (e) {
                // 如果remark不是JSON格式，保持默认值
            }

            // 检测项目数
            const indicatorCount = report.data ? report.data.length : 0;

            return `
                <tr>
                    <td>${report.report_number || '-'}</td>
                    <td>${report.sample_number || '-'}</td>
                    <td>${report.sample_type_name || '-'}</td>
                    <td>${customerUnit}</td>
                    <td>${customerPlant}</td>
                    <td><span class="badge bg-info">${indicatorCount} 项</span></td>
                    <td>${statusBadge}</td>
                    <td>${formatDateTime(report.created_at)}</td>
                    <td class="text-truncate" style="max-width: 200px;" title="${rejectReason}">${rejectReason}</td>
                    <td>
                        <button class="btn btn-sm btn-warning" onclick="editPendingReport(${report.id})">
                            <i class="bi bi-pencil"></i> 编辑
                        </button>
                        <button class="btn btn-sm btn-info" onclick="showReviewDetailModal(${report.id})">
                            <i class="bi bi-eye"></i> 预览
                        </button>
                        <button class="btn btn-sm btn-primary" onclick="submitPendingReport(${report.id})">
                            <i class="bi bi-send"></i> 提交
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deletePendingReport(${report.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('加载待提交报告失败:', error);
        showToast('加载待提交报告失败', 'error');
    }
}

async function submitPendingReport(reportId) {
    if (!confirm('确定要提交此报告到审核吗？')) return;

    try {
        await apiRequest(`/api/reports/${reportId}/submit`, {
            method: 'POST'
        });

        showToast('报告已提交审核');
        loadPendingReports();
    } catch (error) {
        console.error('提交报告失败:', error);
        showToast('提交报告失败: ' + error.message, 'error');
    }
}

async function deletePendingReport(reportId) {
    if (!confirm('确定要删除这个报告吗？此操作不可恢复！')) return;

    try {
        await apiRequest(`/api/reports/${reportId}`, {
            method: 'DELETE'
        });

        showToast('报告已删除');
        loadPendingReports();
    } catch (error) {
        console.error('删除报告失败:', error);
        showToast('删除报告失败: ' + error.message, 'error');
    }
}

// 全局变量：存储当前编辑的报告数据
let editingReportData = null;
let editReportIndicators = [];

async function editPendingReport(reportId) {
    try {
        // 加载报告详情
        const report = await apiRequest(`/api/reports/${reportId}`);

        // 保存到全局变量
        editingReportData = report;

        // 显示编辑标签页
        document.getElementById('edit-report-tab-li').style.display = 'block';
        const editTab = new bootstrap.Tab(document.getElementById('edit-report-tab'));
        editTab.show();

        // 设置报告ID显示
        document.getElementById('editReportId').textContent = `报告 #${report.id}`;

        // 填充基本信息
        document.getElementById('editReportNumber').value = report.report_number || '';
        document.getElementById('editReportDate').value = report.report_date || '';
        document.getElementById('editSampleNumber').value = report.sample_number || '';
        document.getElementById('editSampleType').value = report.sample_type_name || '';
        document.getElementById('editSampleSource').value = report.sample_source || '';
        updateSampleSourceLabels('edit', report.sample_source || '');
        document.getElementById('editSampleStatus').value = report.sample_status || '';
        document.getElementById('editSampler').value = report.sampler || '';
        document.getElementById('editSamplingDate').value = report.sampling_date || '';
        document.getElementById('editSampleReceivedDate').value = report.sample_received_date || '';
        document.getElementById('editDetectionDate').value = report.detection_date || '';
        document.getElementById('editSamplingLocation').value = report.sampling_location || '';
        document.getElementById('editSamplingBasis').value = report.sampling_basis || '';
        document.getElementById('editProductStandard').value = report.product_standard || '';
        document.getElementById('editTestConclusion').value = report.test_conclusion || '';
        document.getElementById('editDetectionItems').value = report.detection_items_description || '';
        document.getElementById('editAdditionalInfo').value = report.additional_info || '';

        // 解析并填充客户信息
        try {
            if (report.remark) {
                const customerInfo = JSON.parse(report.remark);
                document.getElementById('editCustomerUnit').value = customerInfo.customer_unit || '';
                document.getElementById('editCustomerPlant').value = customerInfo.customer_plant || '';
                document.getElementById('editCustomerAddress').value = customerInfo.customer_address || '';
                document.getElementById('editCustomerContact').value = customerInfo.customer_contact || '';
                document.getElementById('editCustomerPhone').value = customerInfo.customer_phone || '';
                document.getElementById('editCustomerEmail').value = customerInfo.customer_email || '';
            }
        } catch (e) {
            // 如果remark不是JSON格式，清空客户信息字段
            document.getElementById('editCustomerUnit').value = '';
            document.getElementById('editCustomerPlant').value = '';
            document.getElementById('editCustomerAddress').value = '';
            document.getElementById('editCustomerContact').value = '';
            document.getElementById('editCustomerPhone').value = '';
            document.getElementById('editCustomerEmail').value = '';
        }

        // 填充检测项目数据
        if (report.data && report.data.length > 0) {
            // 按sort_order排序
            editReportIndicators = report.data.sort((a, b) => a.sort_order - b.sort_order);
            renderEditIndicatorsTable();
        }

        showToast('报告数据已加载，可以开始编辑');
    } catch (error) {
        console.error('加载报告详情失败:', error);
        showToast('加载报告详情失败: ' + error.message, 'error');
    }
}

// 渲染编辑页面的检测项目表格
function renderEditIndicatorsTable() {
    const tbody = document.getElementById('editIndicatorsTableBody');
    if (!tbody) return;

    tbody.innerHTML = editReportIndicators.map((ind, index) => `
        <tr data-index="${index}">
            <td class="text-center">${index + 1}</td>
            <td>
                <input type="text" class="form-control form-control-sm"
                       value="${escapeHtml(ind.indicator_name || '')}"
                       onchange="updateEditIndicatorField(${index}, 'indicator_name', this.value)"
                       placeholder="检测项目名称">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm"
                       value="${escapeHtml(ind.unit || '')}"
                       onchange="updateEditIndicatorField(${index}, 'unit', this.value)">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm"
                       value="${escapeHtml(ind.measured_value || '')}"
                       onchange="updateEditIndicatorField(${index}, 'measured_value', this.value)">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm"
                       value="${escapeHtml(ind.limit_value || '')}"
                       onchange="updateEditIndicatorField(${index}, 'limit_value', this.value)">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm"
                       value="${escapeHtml(ind.detection_method || '')}"
                       onchange="updateEditIndicatorField(${index}, 'detection_method', this.value)">
            </td>
            <td class="text-center">
                <button class="btn btn-sm btn-outline-primary" onclick="moveEditIndicator(${index}, 'up')" ${index === 0 ? 'disabled' : ''}>
                    <i class="bi bi-arrow-up"></i>
                </button>
                <button class="btn btn-sm btn-outline-primary" onclick="moveEditIndicator(${index}, 'down')"
                        ${index === editReportIndicators.length - 1 ? 'disabled' : ''}>
                    <i class="bi bi-arrow-down"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// 更新编辑页面的指标字段
function updateEditIndicatorField(index, field, value) {
    if (editReportIndicators[index]) {
        editReportIndicators[index][field] = value;
    }
}

// 移动编辑页面的检测项目顺序
function moveEditIndicator(index, direction) {
    if (direction === 'up' && index > 0) {
        [editReportIndicators[index], editReportIndicators[index - 1]] =
        [editReportIndicators[index - 1], editReportIndicators[index]];
    } else if (direction === 'down' && index < editReportIndicators.length - 1) {
        [editReportIndicators[index], editReportIndicators[index + 1]] =
        [editReportIndicators[index + 1], editReportIndicators[index]];
    }
    renderEditIndicatorsTable();
}

// 取消编辑报告
function cancelEditReport() {
    // 隐藏编辑标签页
    document.getElementById('edit-report-tab-li').style.display = 'none';

    // 切换回待提交报告标签
    const pendingTab = new bootstrap.Tab(document.getElementById('pending-reports-tab'));
    pendingTab.show();

    // 清空编辑数据
    editingReportData = null;
    editReportIndicators = [];
}

// 保存编辑的报告
async function saveEditReport(submitAfterSave = false) {
    try {
        if (!editingReportData) {
            showToast('没有正在编辑的报告', 'error');
            return;
        }

        // 验证必填字段
        const sampleNumber = document.getElementById('editSampleNumber').value.trim();
        if (!sampleNumber) {
            showToast('请填写样品编号', 'error');
            return;
        }

        // 收集基本信息（新字段）
        const reportDate = document.getElementById('editReportDate').value || null;
        const sampleSource = document.getElementById('editSampleSource').value.trim();
        const sampler = document.getElementById('editSampler').value.trim();
        const samplingDate = document.getElementById('editSamplingDate').value || null;
        const samplingBasis = document.getElementById('editSamplingBasis').value.trim();
        const sampleReceivedDate = document.getElementById('editSampleReceivedDate').value || null;
        const samplingLocation = document.getElementById('editSamplingLocation').value.trim();
        const sampleStatus = document.getElementById('editSampleStatus').value.trim();
        const detectionDate = document.getElementById('editDetectionDate').value || new Date().toISOString().split('T')[0];
        const productStandard = document.getElementById('editProductStandard').value.trim();
        const testConclusion = document.getElementById('editTestConclusion').value;
        const detectionItems = document.getElementById('editDetectionItems').value.trim();
        const additionalInfo = document.getElementById('editAdditionalInfo').value.trim();

        // 收集客户信息
        const customerUnit = document.getElementById('editCustomerUnit').value.trim();
        const customerPlant = document.getElementById('editCustomerPlant').value.trim();
        const customerAddress = document.getElementById('editCustomerAddress').value.trim();
        const customerContact = document.getElementById('editCustomerContact').value.trim();
        const customerPhone = document.getElementById('editCustomerPhone').value.trim();
        const customerEmail = document.getElementById('editCustomerEmail').value.trim();

        // 构建报告数据
        const reportData = {
            sample_number: sampleNumber,
            sample_type_id: editingReportData.sample_type_id,
            report_date: reportDate,
            sample_source: sampleSource,
            sampler: sampler,
            sampling_date: samplingDate,
            sampling_basis: samplingBasis,
            sample_received_date: sampleReceivedDate,
            sampling_location: samplingLocation,
            sample_status: sampleStatus,
            detection_date: detectionDate,
            product_standard: productStandard,
            test_conclusion: testConclusion,
            detection_items_description: detectionItems,
            additional_info: additionalInfo,
            detection_person: '',
            review_person: '',
            remark: JSON.stringify({
                customer_unit: customerUnit,
                customer_plant: customerPlant,
                customer_address: customerAddress,
                customer_contact: customerContact,
                customer_phone: customerPhone,
                customer_email: customerEmail
            }),
            review_status: 'draft',
            data: editReportIndicators.map((ind, index) => ({
                indicator_id: ind.indicator_id,
                indicator_name: ind.indicator_name,
                unit: ind.unit,
                measured_value: ind.measured_value || '',
                limit_value: ind.limit_value,
                detection_method: ind.detection_method,
                remark: '',
                sort_order: index
            }))
        };

        // 更新报告
        await apiRequest(`/api/reports/${editingReportData.id}`, {
            method: 'PUT',
            body: JSON.stringify(reportData)
        });

        showToast('报告保存成功');

        // 如果需要提交审核
        if (submitAfterSave) {
            await apiRequest(`/api/reports/${editingReportData.id}/submit`, {
                method: 'POST'
            });
            showToast('报告已提交审核');
        }

        // 返回待提交报告列表
        cancelEditReport();
        loadPendingReports();

    } catch (error) {
        console.error('保存报告失败:', error);
        showToast('保存报告失败: ' + error.message, 'error');
    }
}

// ==================== 已提交报告 ====================

async function loadSubmittedReports() {
    try {
        const sampleNumber = document.getElementById('submittedSearchSampleNumber').value;
        const status = document.getElementById('submittedSearchStatus').value;
        const companyId = document.getElementById('submittedSearchCompany').value;
        const date = document.getElementById('submittedSearchDate').value;

        let url = '/api/reports/submitted?';
        if (sampleNumber) url += `sample_number=${sampleNumber}&`;
        if (status) url += `status=${status}&`;
        if (companyId) url += `company_id=${companyId}&`;
        if (date) url += `date=${date}&`;

        const reports = await apiRequest(url);

        const tbody = document.getElementById('submittedReportsTableBody');

        if (reports.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">暂无已提交报告</td></tr>';
            return;
        }

        tbody.innerHTML = reports.map(report => {
            // 审核状态
            let reviewStatusBadge = '';
            switch (report.review_status) {
                case 'pending':
                    reviewStatusBadge = '<span class="badge bg-warning text-dark">待审核</span>';
                    break;
                case 'approved':
                    reviewStatusBadge = '<span class="badge bg-success">已审核</span>';
                    break;
                case 'rejected':
                    reviewStatusBadge = '<span class="badge bg-danger">已拒绝</span>';
                    break;
                default:
                    reviewStatusBadge = '<span class="badge bg-secondary">未知</span>';
            }

            // 生成状态
            let generateStatusBadge = '';
            if (report.generated_report_path) {
                generateStatusBadge = '<span class="badge bg-primary">已生成</span>';
            } else if (report.review_status === 'approved') {
                generateStatusBadge = '<span class="badge bg-secondary">可生成</span>';
            } else {
                generateStatusBadge = '<span class="badge bg-light text-dark">未生成</span>';
            }

            return `
                <tr>
                    <td>${report.report_number || '-'}</td>
                    <td>${report.sample_number || '-'}</td>
                    <td>${report.sample_type_name || '-'}</td>
                    <td>${report.company_name || '-'}</td>
                    <td>${report.template_name || '-'}</td>
                    <td>${reviewStatusBadge}</td>
                    <td>${generateStatusBadge}</td>
                    <td>${formatDateTime(report.created_at)}</td>
                    <td>
                        <button class="btn btn-sm btn-info" onclick="showReviewDetailModal(${report.id})">
                            <i class="bi bi-eye"></i> 查看
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('加载已提交报告失败:', error);
        showToast('加载已提交报告失败', 'error');
    }
}

// ==================== 报告审核 ====================

async function loadReviewReports() {
    try {
        const sampleNumber = document.getElementById('reviewSearchSampleNumber').value;
        const status = document.getElementById('reviewSearchStatus').value;
        const companyId = document.getElementById('reviewSearchCompany').value;

        let url = '/api/reports/review?';
        if (sampleNumber) url += `sample_number=${sampleNumber}&`;
        if (status) url += `status=${status}&`;
        if (companyId) url += `company_id=${companyId}&`;

        const reports = await apiRequest(url);

        const tbody = document.getElementById('reviewReportsList');

        if (reports.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">暂无报告</td></tr>';
            return;
        }

        tbody.innerHTML = reports.map(report => {
            let statusBadge = '';
            let actionButtons = '';

            switch (report.review_status) {
                case 'draft':
                    statusBadge = '<span class="badge bg-secondary">草稿</span>';
                    break;
                case 'pending':
                    statusBadge = '<span class="badge bg-warning text-dark">待审核</span>';
                    actionButtons = `
                        <button class="btn btn-sm btn-success" onclick="showApproveModal(${report.id})">
                            <i class="bi bi-check-circle"></i> 通过
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="showRejectModal(${report.id})">
                            <i class="bi bi-x-circle"></i> 拒绝
                        </button>
                    `;
                    break;
                case 'approved':
                    statusBadge = '<span class="badge bg-success">已审核</span>';
                    actionButtons = `
                        <button class="btn btn-sm btn-danger" onclick="deleteReport(${report.id}, 'review')">
                            <i class="bi bi-trash"></i> 删除
                        </button>
                    `;
                    break;
                case 'rejected':
                    statusBadge = '<span class="badge bg-danger">已拒绝</span>';
                    actionButtons = `
                        <button class="btn btn-sm btn-danger" onclick="deleteReport(${report.id}, 'review')">
                            <i class="bi bi-trash"></i> 删除
                        </button>
                    `;
                    break;
                default:
                    statusBadge = '<span class="badge bg-secondary">未知</span>';
            }

            return `
                <tr>
                    <td>${report.report_number || '-'}</td>
                    <td>${report.sample_number || '-'}</td>
                    <td>${report.sample_type_name || '-'}</td>
                    <td>${report.company_name || '-'}</td>
                    <td>${statusBadge}</td>
                    <td>${formatDateTime(report.created_at)}</td>
                    <td>${report.detection_date || '-'}</td>
                    <td>
                        <button class="btn btn-sm btn-info" onclick="showReviewDetailModal(${report.id})">
                            <i class="bi bi-eye"></i> 查看
                        </button>
                        ${actionButtons}
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('加载报告审核列表失败:', error);
        showToast('加载报告审核列表失败', 'error');
    }
}

async function showReviewDetailModal(reportId) {
    try {
        const data = await apiRequest(`/api/reports/${reportId}/review-detail`);

        // 解析客户信息
        let customerInfo = {};
        try {
            if (data.report.remark) {
                customerInfo = JSON.parse(data.report.remark);
            }
        } catch (e) {
            console.error('解析客户信息失败:', e);
        }

        // 获取审核状态显示
        const getStatusBadge = (status) => {
            const statusMap = {
                'draft': '<span class="badge bg-secondary">草稿</span>',
                'pending': '<span class="badge bg-warning">待审核</span>',
                'approved': '<span class="badge bg-success">已通过</span>',
                'rejected': '<span class="badge bg-danger">已拒绝</span>'
            };
            return statusMap[status] || '<span class="badge bg-secondary">未知</span>';
        };

        // 创建详情模态框
        const modalHTML = `
            <div class="modal fade" id="reviewDetailModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">报告详情 - ${data.report.report_number} ${getStatusBadge(data.report.review_status)}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body" style="max-height: 80vh; overflow-y: auto;">
                            <h6 class="mb-3"><i class="bi bi-card-list"></i> 基本信息</h6>
                            <div class="row mb-2">
                                <div class="col-md-6"><strong>报告编号：</strong>${data.report.report_number || '-'}</div>
                                <div class="col-md-6"><strong>报告编制日期：</strong>${data.report.report_date ? formatDate(data.report.report_date) : '-'}</div>
                            </div>
                            <div class="row mb-2">
                                <div class="col-md-6"><strong>样品编号：</strong>${data.report.sample_number || '-'}</div>
                                <div class="col-md-6"><strong>样品类型：</strong>${data.report.sample_type_name || '-'}</div>
                            </div>
                            <div class="row mb-2">
                                <div class="col-md-6"><strong>样品来源：</strong>${data.report.sample_source || '-'}</div>
                                <div class="col-md-6"><strong>样品状态：</strong>${data.report.sample_status || '-'}</div>
                            </div>
                            <div class="row mb-2">
                                <div class="col-md-6"><strong>采样人：</strong>${data.report.sampler || '-'}</div>
                                <div class="col-md-6"><strong>采样日期：</strong>${data.report.sampling_date ? formatDate(data.report.sampling_date) : '-'}</div>
                            </div>
                            <div class="row mb-2">
                                <div class="col-md-6"><strong>收样日期：</strong>${data.report.sample_received_date ? formatDate(data.report.sample_received_date) : '-'}</div>
                                <div class="col-md-6"><strong>检测日期：</strong>${data.report.detection_date || '-'}</div>
                            </div>
                            <div class="row mb-2">
                                <div class="col-md-6"><strong>采样地点：</strong>${data.report.sampling_location || '-'}</div>
                                <div class="col-md-6"><strong>采样依据：</strong>${data.report.sampling_basis || '-'}</div>
                            </div>
                            <div class="row mb-2">
                                <div class="col-md-6"><strong>产品标准：</strong>${data.report.product_standard || '-'}</div>
                                <div class="col-md-6"><strong>创建时间：</strong>${data.report.created_at ? formatDateTime(data.report.created_at) : '-'}</div>
                            </div>
                            ${data.report.test_conclusion ? `
                                <div class="row mb-2">
                                    <div class="col-md-12"><strong>检测结论：</strong><br><div class="p-2 bg-light rounded">${data.report.test_conclusion}</div></div>
                                </div>
                            ` : ''}
                            ${data.report.detection_items_description ? `
                                <div class="row mb-2">
                                    <div class="col-md-12"><strong>检测项目：</strong><br><div class="p-2 bg-light rounded">${data.report.detection_items_description}</div></div>
                                </div>
                            ` : ''}
                            ${data.report.additional_info ? `
                                <div class="row mb-2">
                                    <div class="col-md-12"><strong>附加信息：</strong><br><div class="p-2 bg-light rounded">${data.report.additional_info}</div></div>
                                </div>
                            ` : ''}

                            <hr>

                            <h6 class="mb-3"><i class="bi bi-people"></i> 客户信息</h6>
                            <div class="row mb-2">
                                <div class="col-md-6"><strong>被检单位：</strong>${customerInfo.customer_unit || '-'}</div>
                                <div class="col-md-6"><strong>被检水厂：</strong>${customerInfo.customer_plant || '-'}</div>
                            </div>
                            <div class="row mb-2">
                                <div class="col-md-6"><strong>联系人：</strong>${customerInfo.customer_contact || '-'}</div>
                                <div class="col-md-6"><strong>联系电话：</strong>${customerInfo.customer_phone || '-'}</div>
                            </div>
                            <div class="row mb-2">
                                <div class="col-md-6"><strong>电子邮箱：</strong>${customerInfo.customer_email || '-'}</div>
                                <div class="col-md-6"><strong>地址：</strong>${customerInfo.customer_address || '-'}</div>
                            </div>

                            <hr>

                            <h6 class="mb-3"><i class="bi bi-clipboard-data"></i> 检测数据 (${data.detection_data.length} 项)</h6>
                            <div class="table-responsive">
                                <table class="table table-sm table-bordered table-hover">
                                    <thead class="table-light">
                                        <tr>
                                            <th style="width: 5%;">序号</th>
                                            <th style="width: 20%;">检测项目</th>
                                            <th style="width: 15%;">检测值</th>
                                            <th style="width: 10%;">单位</th>
                                            <th style="width: 15%;">限值</th>
                                            <th style="width: 35%;">检测方法</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${data.detection_data.map((item, index) => `
                                            <tr>
                                                <td class="text-center">${index + 1}</td>
                                                <td>${item.indicator_name}</td>
                                                <td>${item.measured_value || '-'}</td>
                                                <td>${item.unit || '-'}</td>
                                                <td>${item.limit_value || '-'}</td>
                                                <td class="small">${item.detection_method || '-'}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>

                            ${data.template_fields && data.template_fields.length > 0 ? `
                                <hr>
                                <h6 class="mb-3"><i class="bi bi-file-text"></i> 模板字段</h6>
                                <div class="row">
                                    ${data.template_fields.map(field => `
                                        <div class="col-md-4 mb-2">
                                            <strong>${field.field_display_name || field.field_name}：</strong>
                                            ${field.field_value}
                                        </div>
                                    `).join('')}
                                </div>
                            ` : ''}

                            ${data.review_history && data.review_history.length > 0 || data.report.review_status !== 'draft' ? `
                                <hr>
                                <h6 class="mb-3"><i class="bi bi-chat-left-text"></i> 审核信息</h6>

                                ${data.report.review_status === 'pending' ? `
                                    <div class="alert alert-warning mb-3">
                                        <strong>当前状态：</strong>等待审核中
                                    </div>
                                ` : data.report.review_status === 'draft' ? `
                                    <div class="alert alert-secondary mb-3">
                                        <strong>当前状态：</strong>草稿，尚未提交审核
                                    </div>
                                ` : ''}

                                ${data.review_history && data.review_history.length > 0 ? `
                                    <h6 class="small text-muted mb-2">审核历史记录 (${data.review_history.length} 条)</h6>
                                    ${data.review_history.map((history, index) => `
                                        <div class="card mb-2 ${index === 0 ? 'border-primary' : ''}">
                                            <div class="card-body py-2 px-3">
                                                <div class="d-flex justify-content-between align-items-start">
                                                    <div class="flex-grow-1">
                                                        <div class="mb-1">
                                                            <span class="badge bg-${history.review_status === 'approved' ? 'success' : history.review_status === 'rejected' ? 'danger' : 'warning'}">
                                                                ${history.review_status === 'approved' ? '通过' : history.review_status === 'rejected' ? '拒绝' : '待审核'}
                                                            </span>
                                                            <strong class="ms-2">${history.reviewer_name || '未知审核人'}</strong>
                                                            ${index === 0 ? '<span class="badge bg-info ms-1">最新</span>' : ''}
                                                        </div>
                                                        ${history.review_comment ? `
                                                            <div class="small text-muted">
                                                                ${history.review_comment}
                                                            </div>
                                                        ` : '<div class="small text-muted fst-italic">无审核意见</div>'}
                                                    </div>
                                                    <div class="text-end ms-3">
                                                        <small class="text-muted">
                                                            ${new Date(history.reviewed_at).toLocaleString('zh-CN', {
                                                                year: 'numeric',
                                                                month: '2-digit',
                                                                day: '2-digit',
                                                                hour: '2-digit',
                                                                minute: '2-digit'
                                                            })}
                                                        </small>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    `).join('')}
                                ` : data.report.review_comment ? `
                                    <div class="alert alert-${data.report.review_status === 'rejected' ? 'danger' : 'success'} mb-0">
                                        <div class="d-flex justify-content-between align-items-start">
                                            <div>
                                                <strong>${data.report.review_status === 'rejected' ? '拒绝' : '通过'}：</strong>
                                                ${data.report.review_comment}
                                            </div>
                                            ${data.report.reviewed_at ? `
                                                <small class="text-muted">${new Date(data.report.reviewed_at).toLocaleString('zh-CN')}</small>
                                            ` : ''}
                                        </div>
                                    </div>
                                ` : ''}
                            ` : ''}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 移除旧模态框
        const oldModal = document.getElementById('reviewDetailModal');
        if (oldModal) oldModal.remove();

        // 添加新模态框
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        const modal = new bootstrap.Modal(document.getElementById('reviewDetailModal'));
        modal.show();

    } catch (error) {
        console.error('加载报告详情失败:', error);
        showToast('加载报告详情失败', 'error');
    }
}

async function showApproveModal(reportId) {
    const comment = prompt('审核意见（可选）:');
    if (comment === null) return; // 用户点击取消

    try {
        await apiRequest(`/api/reports/${reportId}/approve`, {
            method: 'POST',
            body: JSON.stringify({ comment: comment || '' })
        });

        showToast('审核通过');
        loadReviewReports();
    } catch (error) {
        console.error('审核通过失败:', error);
        showToast('审核通过失败: ' + error.message, 'error');
    }
}

async function showRejectModal(reportId) {
    const comment = prompt('请填写拒绝原因（必填）:');
    if (!comment || comment.trim() === '') {
        showToast('拒绝原因不能为空', 'warning');
        return;
    }

    try {
        await apiRequest(`/api/reports/${reportId}/reject`, {
            method: 'POST',
            body: JSON.stringify({ comment: comment })
        });

        showToast('已拒绝');
        loadReviewReports();
    } catch (error) {
        console.error('拒绝失败:', error);
        showToast('拒绝失败: ' + error.message, 'error');
    }
}

// ==================== 报告生成 ====================

async function loadGenReports() {
    try {
        const sampleNumber = document.getElementById('genSearchSampleNumber').value;
        const companyId = document.getElementById('genSearchCompany').value;

        let url = '/api/reports/review?status=approved&';
        if (sampleNumber) url += `sample_number=${sampleNumber}&`;
        if (companyId) url += `company_id=${companyId}&`;

        const reports = await apiRequest(url);

        const tbody = document.getElementById('genReportsList');

        if (reports.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">暂无已审核通过的报告</td></tr>';
            return;
        }

        tbody.innerHTML = reports.map(report => {
            const generateStatusBadge = report.generated_report_path
                ? '<span class="badge bg-success">已生成</span>'
                : '<span class="badge bg-secondary">未生成</span>';

            const actionButtons = report.generated_report_path
                ? `<button class="btn btn-sm btn-primary me-1" onclick="downloadReport(${report.id})">
                       <i class="bi bi-download"></i> 下载
                   </button>
                   <button class="btn btn-sm btn-secondary me-1" onclick="returnReport(${report.id})">
                       <i class="bi bi-arrow-return-left"></i> 退回
                   </button>
                   <button class="btn btn-sm btn-danger" onclick="deleteReport(${report.id}, 'gen')">
                       <i class="bi bi-trash"></i> 删除
                   </button>`
                : `<button class="btn btn-sm btn-success me-1" onclick="generateReport(${report.id})">
                       <i class="bi bi-file-earmark-plus"></i> 生成报告
                   </button>
                   <button class="btn btn-sm btn-secondary me-1" onclick="returnReport(${report.id})">
                       <i class="bi bi-arrow-return-left"></i> 退回
                   </button>
                   <button class="btn btn-sm btn-danger" onclick="deleteReport(${report.id}, 'gen')">
                       <i class="bi bi-trash"></i> 删除
                   </button>`;

            return `
                <tr>
                    <td>${report.report_number || '-'}</td>
                    <td>${report.sample_number || '-'}</td>
                    <td>${report.sample_type_name || '-'}</td>
                    <td>${report.company_name || '-'}</td>
                    <td>${report.review_person || '-'}</td>
                    <td>${report.review_time ? new Date(report.review_time).toLocaleString('zh-CN') : '-'}</td>
                    <td>${generateStatusBadge}</td>
                    <td>${actionButtons}</td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('加载报告生成列表失败:', error);
        showToast('加载报告生成列表失败', 'error');
    }
}

async function generateReport(reportId) {
    try {
        // 显示模板选择对话框
        await showTemplateSelectModal(reportId);

    } catch (error) {
        console.error('生成报告失败:', error);
        showToast('生成报告失败: ' + error.message, 'error');
    }
}

// 显示模板选择对话框
async function showTemplateSelectModal(reportId) {
    try {
        // 加载模板列表
        const templates = await apiRequest('/api/report-templates');

        if (templates.length === 0) {
            showToast('没有可用的报告模板，请先导入模板', 'warning');
            return;
        }

        // 填充模板下拉列表
        const selectElement = document.getElementById('selectedTemplateId');
        selectElement.innerHTML = '<option value="">-- 请选择模板 --</option>' +
            templates.map(t => `<option value="${t.id}">${t.name} ${t.sample_type_name ? `(${t.sample_type_name})` : ''}</option>`).join('');

        // 监听模板选择变化
        selectElement.onchange = function() {
            const templateId = this.value;
            const templateInfo = document.getElementById('templateInfo');
            const templateInfoContent = document.getElementById('templateInfoContent');

            if (templateId) {
                const template = templates.find(t => t.id == templateId);
                if (template) {
                    templateInfoContent.innerHTML = `
                        <div><strong>模板名称：</strong>${template.name}</div>
                        <div><strong>样品类型：</strong>${template.sample_type_name || '未指定'}</div>
                        <div><strong>描述：</strong>${template.description || '无'}</div>
                    `;
                    templateInfo.classList.remove('d-none');
                }
            } else {
                templateInfo.classList.add('d-none');
            }
        };

        // 显示对话框
        const modal = new bootstrap.Modal(document.getElementById('templateSelectModal'));
        modal.show();

        // 绑定确认生成按钮
        document.getElementById('confirmGenerateBtn').onclick = async function() {
            const selectedTemplateId = document.getElementById('selectedTemplateId').value;

            if (!selectedTemplateId) {
                showToast('请选择一个模板', 'warning');
                return;
            }

            modal.hide();

            // 执行生成报告
            await executeGenerateReport(reportId, selectedTemplateId);
        };

    } catch (error) {
        console.error('加载模板列表失败:', error);
        showToast('加载模板列表失败: ' + error.message, 'error');
    }
}

// 执行生成报告
async function executeGenerateReport(reportId, templateId) {
    try {
        showToast('正在生成报告，请稍候...', 'warning');

        const result = await apiRequest(`/api/reports/${reportId}/generate`, {
            method: 'POST',
            body: JSON.stringify({
                template_id: parseInt(templateId)
            })
        });

        showToast('报告生成成功！');
        loadGenReports();  // 刷新列表

    } catch (error) {
        console.error('生成报告失败:', error);
        showToast('生成报告失败: ' + error.message, 'error');
    }
}

async function downloadReport(reportId) {
    try {
        const response = await fetch(`/api/reports/${reportId}/download`);
        if (!response.ok) {
            throw new Error('下载失败');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'report.xlsx';
        if (contentDisposition) {
            const match = contentDisposition.match(/filename="?([^";]+)"?/);
            if (match) filename = match[1];
        }

        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        showToast('报告下载成功');

    } catch (error) {
        console.error('下载报告失败:', error);
        showToast('下载报告失败: ' + error.message, 'error');
    }
}

async function deleteReport(reportId, module) {
    if (!confirm('确定要删除此报告吗？删除后无法恢复！')) {
        return;
    }

    try {
        await apiRequest(`/api/reports/${reportId}`, {
            method: 'DELETE'
        });

        showToast('报告删除成功');

        // 根据模块刷新相应的列表
        if (module === 'review') {
            loadReviewReports();
        } else if (module === 'gen') {
            loadGenReports();
        } else if (module === 'submitted') {
            loadSubmittedReports();
        }

    } catch (error) {
        console.error('删除报告失败:', error);
        showToast('删除报告失败: ' + error.message, 'error');
    }
}

// ==================== 退回报告功能 ====================
async function returnReport(reportId) {
    const reason = prompt('请输入退回原因（可选）：', '');

    // 用户点击取消
    if (reason === null) {
        return;
    }

    if (!confirm('确定要将此报告退回到审核状态吗？\n\n退回后：\n- 报告状态将变为"待审核"\n- 已生成的报告文件将被清除\n- 需要重新审核后才能再次生成')) {
        return;
    }

    try {
        await apiRequest(`/api/reports/${reportId}/return`, {
            method: 'POST',
            body: JSON.stringify({
                reason: reason.trim()
            })
        });

        showToast('报告已成功退回到审核状态');

        // 刷新报告生成列表
        loadGenReports();

    } catch (error) {
        console.error('退回报告失败:', error);
        showToast('退回报告失败: ' + error.message, 'error');
    }
}

// ==================== 新建报告功能 ====================
let reportIndicators = []; // 存储当前报告的检测项目列表
let allCustomers = []; // 存储所有客户数据
let selectedCustomerId = null; // 当前选中的客户ID

// 初始化新建报告页面
function initNewReportPage() {
    // 加载样品类型列表
    loadSampleTypesForNewReport();

    // 加载客户列表
    loadCustomersForReport();

    // 设置默认值
    setNewReportDefaults();

    // 绑定事件
    const sampleTypeSelect = document.getElementById('newReportSampleType');
    const loadBtn = document.getElementById('loadIndicatorsBtn');
    const saveBtn = document.getElementById('saveNewReportBtn');
    const resetBtn = document.getElementById('resetNewReportBtn');

    // 客户信息相关事件
    const customerPlantSelect = document.getElementById('customerPlantSelect');
    const loadCustomerBtn = document.getElementById('loadCustomerInfoBtn');

    if (sampleTypeSelect) {
        sampleTypeSelect.addEventListener('change', function() {
            loadBtn.disabled = !this.value;
        });
    }

    if (loadBtn) {
        loadBtn.addEventListener('click', loadReportIndicators);
    }

    if (saveBtn) {
        saveBtn.addEventListener('click', saveNewReport);
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', resetNewReportForm);
    }

    // 客户信息事件绑定
    if (customerPlantSelect) {
        customerPlantSelect.addEventListener('change', onCustomerPlantChange);
    }

    if (loadCustomerBtn) {
        loadCustomerBtn.addEventListener('click', loadCustomerInfo);
    }

    // 样品来源下拉菜单事件绑定
    initSampleSourceDropdown();
}

// 设置新建报告的默认值
function setNewReportDefaults() {
    // 设置报告编制日期为当天
    const today = new Date().toISOString().split('T')[0];
    const reportDateInput = document.getElementById('newReportDate');
    if (reportDateInput) {
        reportDateInput.value = today;
    }

    // 设置样品来源默认值
    const sampleSourceInput = document.getElementById('newSampleSource');
    if (sampleSourceInput && !sampleSourceInput.value) {
        sampleSourceInput.value = '委托采样';
    }
    updateSampleSourceLabels('new', sampleSourceInput ? sampleSourceInput.value : '');

    // 监听手动输入变化
    if (sampleSourceInput) {
        sampleSourceInput.addEventListener('input', function() {
            updateSampleSourceLabels('new', this.value.trim());
        });
    }
}

// 初始化样品来源下拉菜单
function initSampleSourceDropdown() {
    const sourceInput = document.getElementById('newSampleSource');
    const sourceDropdown = document.getElementById('sampleSourceDropdown');

    if (!sourceInput || !sourceDropdown) return;

    // 点击输入框显示下拉菜单
    sourceInput.addEventListener('focus', function() {
        sourceDropdown.classList.add('show');
    });

    // 点击输入框显示下拉菜单
    sourceInput.addEventListener('click', function() {
        sourceDropdown.classList.add('show');
    });

    // 点击外部区域关闭下拉菜单
    document.addEventListener('click', function(e) {
        if (!sourceInput.contains(e.target) && !sourceDropdown.contains(e.target)) {
            sourceDropdown.classList.remove('show');
        }
    });
}

// 根据样品来源切换标签文字及字段状态
function updateSampleSourceLabels(prefix, source) {
    const samplerLabel = document.getElementById(prefix + 'SamplerLabel');
    const dateLabel = document.getElementById(prefix + 'SamplingDateLabel');
    const samplerInput = document.getElementById(prefix === 'new' ? 'newSampler' : 'editSampler');
    const locationInput = document.getElementById(prefix === 'new' ? 'newSamplingLocation' : 'editSamplingLocation');
    const basisInput = document.getElementById(prefix === 'new' ? 'newSamplingBasis' : 'editSamplingBasis');
    if (source === '委托送样') {
        if (samplerLabel) samplerLabel.textContent = '送样人';
        if (dateLabel) dateLabel.textContent = '送样日期';
        if (samplerInput) samplerInput.placeholder = '送样人姓名';
        if (locationInput) {
            locationInput._prevValue = locationInput.value;
            locationInput.value = '-';
            locationInput.disabled = true;
        }
        if (basisInput) {
            basisInput._prevValue = basisInput.value;
            basisInput.value = '-';
            basisInput.disabled = true;
        }
    } else {
        if (samplerLabel) samplerLabel.textContent = '采样人';
        if (dateLabel) dateLabel.textContent = '采样日期';
        if (samplerInput) samplerInput.placeholder = '采样人姓名';
        if (locationInput) {
            locationInput.disabled = false;
            if (locationInput.value === '-') {
                locationInput.value = locationInput._prevValue || '';
            }
        }
        if (basisInput) {
            basisInput.disabled = false;
            if (basisInput.value === '-') {
                basisInput.value = basisInput._prevValue || 'GB/T 5750.2-2023';
            }
        }
    }
}

// 选择样品来源
function selectSampleSource(source) {
    const sourceInput = document.getElementById('newSampleSource');
    const sourceDropdown = document.getElementById('sampleSourceDropdown');

    if (sourceInput) {
        sourceInput.value = source;
    }

    if (sourceDropdown) {
        sourceDropdown.classList.remove('show');
    }

    updateSampleSourceLabels('new', source);
}

// 加载样品类型列表
async function loadSampleTypesForNewReport() {
    try {
        const sampleTypes = await apiRequest('/api/sample-types');
        const select = document.getElementById('newReportSampleType');

        if (select) {
            select.innerHTML = '<option value="">请选择样品类型...</option>';
            sampleTypes.forEach(st => {
                const option = document.createElement('option');
                option.value = st.id;
                option.textContent = `${st.name} (${st.code})`;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('加载样品类型失败:', error);
        showToast('加载样品类型失败', 'error');
    }
}

// 存储所有被检单位列表
let allUnits = [];
let selectedUnit = '';

// 加载客户列表
async function loadCustomersForReport() {
    try {
        allCustomers = await apiRequest('/api/customers');

        // 获取所有不重复的被检单位
        allUnits = [...new Set(allCustomers.map(c => c.inspected_unit).filter(u => u))];

        // 初始化搜索下拉框
        initCustomerUnitSearch();
    } catch (error) {
        console.error('加载客户列表失败:', error);
        showToast('加载客户列表失败', 'error');
    }
}

// 初始化被检单位搜索下拉框
function initCustomerUnitSearch() {
    const unitInput = document.getElementById('customerUnitInput');
    const dropdown = document.getElementById('customerUnitDropdown');

    if (!unitInput || !dropdown) return;

    // 输入事件 - 实时筛选
    unitInput.addEventListener('input', function() {
        const searchText = this.value.trim().toLowerCase();

        if (searchText === '') {
            // 如果清空了输入，显示所有选项
            renderUnitDropdown(allUnits);
        } else {
            // 筛选匹配的被检单位
            const filtered = allUnits.filter(unit =>
                unit.toLowerCase().includes(searchText)
            );
            renderUnitDropdown(filtered);
        }

        // 显示下拉菜单
        dropdown.classList.add('show');
    });

    // 获得焦点时显示所有选项
    unitInput.addEventListener('focus', function() {
        renderUnitDropdown(allUnits);
        dropdown.classList.add('show');
    });

    // 点击外部关闭下拉菜单
    document.addEventListener('click', function(e) {
        if (!unitInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.remove('show');
        }
    });
}

// 渲染被检单位下拉列表
function renderUnitDropdown(units) {
    const dropdown = document.getElementById('customerUnitDropdown');
    if (!dropdown) return;

    if (units.length === 0) {
        dropdown.innerHTML = '<div class="dropdown-item disabled">无匹配结果</div>';
        return;
    }

    dropdown.innerHTML = units.map(unit =>
        `<a class="dropdown-item" href="javascript:void(0)" onclick="selectCustomerUnit('${escapeHtml(unit)}')">${escapeHtml(unit)}</a>`
    ).join('');
}

// 选择被检单位
function selectCustomerUnit(unit) {
    selectedUnit = unit;

    // 更新输入框
    const unitInput = document.getElementById('customerUnitInput');
    if (unitInput) {
        unitInput.value = unit;
    }

    // 关闭下拉菜单
    const dropdown = document.getElementById('customerUnitDropdown');
    if (dropdown) {
        dropdown.classList.remove('show');
    }

    // 触发单位变化事件
    onCustomerUnitChange();
}

// 被检单位选择变化
function onCustomerUnitChange() {
    const plantSelect = document.getElementById('customerPlantSelect');
    const loadBtn = document.getElementById('loadCustomerInfoBtn');

    if (!selectedUnit) {
        plantSelect.innerHTML = '<option value="">请先选择被检单位...</option>';
        plantSelect.disabled = true;
        loadBtn.disabled = true;
        return;
    }

    // 筛选该被检单位下的所有水厂
    const customers = allCustomers.filter(c => c.inspected_unit === selectedUnit);

    plantSelect.innerHTML = '<option value="">请选择被检水厂...</option>';
    customers.forEach(customer => {
        const option = document.createElement('option');
        option.value = customer.id;
        option.textContent = customer.water_plant || '（无水厂名称）';
        plantSelect.appendChild(option);
    });

    plantSelect.disabled = false;
    loadBtn.disabled = true;
}

// 被检水厂选择变化
function onCustomerPlantChange() {
    const plantSelect = document.getElementById('customerPlantSelect');
    const loadBtn = document.getElementById('loadCustomerInfoBtn');

    const customerId = plantSelect.value;
    loadBtn.disabled = !customerId;

    if (customerId) {
        selectedCustomerId = parseInt(customerId);
    } else {
        selectedCustomerId = null;
    }
}

// 加载客户信息
function loadCustomerInfo() {
    if (!selectedCustomerId) {
        showToast('请先选择被检水厂', 'warning');
        return;
    }

    const customer = allCustomers.find(c => c.id === selectedCustomerId);

    if (!customer) {
        showToast('未找到客户信息', 'error');
        return;
    }

    // 填充客户信息字段
    document.getElementById('customerAddress').value = customer.unit_address || '';
    document.getElementById('customerContact').value = customer.contact_person || '';
    document.getElementById('customerPhone').value = customer.contact_phone || '';
    document.getElementById('customerEmail').value = customer.email || '';

    // 显示客户信息字段
    document.getElementById('customerInfoFields').style.display = 'block';

    showToast('客户信息已加载，可手动编辑', 'success');
}

// 加载检测项目
async function loadReportIndicators() {
    const sampleTypeId = document.getElementById('newReportSampleType').value;

    if (!sampleTypeId) {
        showToast('请先选择样品类型', 'warning');
        return;
    }

    try {
        const indicators = await apiRequest(`/api/template-indicators?sample_type_id=${sampleTypeId}`);

        if (indicators.length === 0) {
            showToast('该样品类型没有配置检测项目', 'warning');
            return;
        }

        reportIndicators = indicators.map((ind, index) => ({
            ...ind,
            order: index,
            measured_value: ind.default_value || ''
        }));

        renderIndicatorsTable();
        document.getElementById('indicatorsCard').style.display = 'block';

    } catch (error) {
        console.error('加载检测项目失败:', error);
        showToast('加载检测项目失败: ' + error.message, 'error');
    }
}

// 渲染检测项目表格
function renderIndicatorsTable() {
    const tbody = document.getElementById('indicatorsTableBody');

    if (!tbody) return;

    tbody.innerHTML = reportIndicators.map((ind, index) => `
        <tr data-index="${index}">
            <td class="text-center">${index + 1}</td>
            <td>
                <input type="text" class="form-control form-control-sm"
                       value="${escapeHtml(ind.indicator_name || '')}"
                       onchange="updateIndicatorField(${index}, 'indicator_name', this.value)"
                       placeholder="检测项目名称">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm"
                       value="${escapeHtml(ind.unit || '')}"
                       onchange="updateIndicatorField(${index}, 'unit', this.value)"
                       placeholder="单位">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm"
                       value="${escapeHtml(ind.measured_value || '')}"
                       onchange="updateIndicatorField(${index}, 'measured_value', this.value)"
                       placeholder="检测结果">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm"
                       value="${escapeHtml(ind.limit_value || '')}"
                       onchange="updateIndicatorField(${index}, 'limit_value', this.value)"
                       placeholder="限值">
            </td>
            <td>
                <input type="text" class="form-control form-control-sm"
                       value="${escapeHtml(ind.detection_method || '')}"
                       onchange="updateIndicatorField(${index}, 'detection_method', this.value)"
                       placeholder="检测方法">
            </td>
            <td class="text-center">
                <button class="btn btn-sm btn-outline-primary"
                        onclick="moveIndicator(${index}, 'up')"
                        ${index === 0 ? 'disabled' : ''}
                        title="上移">
                    <i class="bi bi-arrow-up"></i>
                </button>
                <button class="btn btn-sm btn-outline-primary"
                        onclick="moveIndicator(${index}, 'down')"
                        ${index === reportIndicators.length - 1 ? 'disabled' : ''}
                        title="下移">
                    <i class="bi bi-arrow-down"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// HTML转义函数
function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// 更新检测项目字段（通用）
function updateIndicatorField(index, field, value) {
    if (reportIndicators[index]) {
        reportIndicators[index][field] = value;
    }
}

// 移动检测项目顺序
function moveIndicator(index, direction) {
    if (direction === 'up' && index > 0) {
        [reportIndicators[index], reportIndicators[index - 1]] =
        [reportIndicators[index - 1], reportIndicators[index]];
    } else if (direction === 'down' && index < reportIndicators.length - 1) {
        [reportIndicators[index], reportIndicators[index + 1]] =
        [reportIndicators[index + 1], reportIndicators[index]];
    }

    renderIndicatorsTable();
}

// 保存新报告
async function saveNewReport() {
    // 获取基本信息
    const reportNumber = document.getElementById('newReportNumber').value.trim();
    const sampleNumber = document.getElementById('newReportSampleNumber').value.trim();
    const sampleTypeId = document.getElementById('newReportSampleType').value;

    // 验证必填字段
    if (!reportNumber) {
        showToast('报告编号不能为空', 'warning');
        return;
    }

    if (!sampleNumber) {
        showToast('样品编号不能为空', 'warning');
        return;
    }

    if (!sampleTypeId) {
        showToast('请选择样品类型', 'warning');
        return;
    }

    if (reportIndicators.length === 0) {
        showToast('请先加载检测项目', 'warning');
        return;
    }

    // 验证至少有一个检测项目有名称
    const validIndicators = reportIndicators.filter(ind => ind.indicator_name && ind.indicator_name.trim());
    if (validIndicators.length === 0) {
        showToast('至少需要一个有效的检测项目', 'warning');
        return;
    }

    // 获取基本信息（新字段）
    const reportDate = document.getElementById('newReportDate').value || null;
    const sampleSource = document.getElementById('newSampleSource').value.trim();
    const sampler = document.getElementById('newSampler').value.trim();
    const samplingDate = document.getElementById('newSamplingDate').value || null;
    const samplingBasis = document.getElementById('newSamplingBasis').value.trim();
    const sampleReceivedDate = document.getElementById('newSampleReceivedDate').value || null;
    const samplingLocation = document.getElementById('newSamplingLocation').value.trim();
    const sampleStatus = document.getElementById('newSampleStatus').value.trim();
    const detectionDate = document.getElementById('newDetectionDate').value || new Date().toISOString().split('T')[0];
    const productStandard = document.getElementById('newProductStandard').value.trim();
    const testItems = document.getElementById('newTestItems').value.trim();
    const testConclusion = document.getElementById('newTestConclusion').value;
    const additionalInfo = document.getElementById('newAdditionalInfo').value.trim();

    // 获取客户信息（可选）
    const customerUnit = document.getElementById('customerUnitInput').value.trim() || '';
    const customerPlant = document.getElementById('customerPlantSelect').options[
        document.getElementById('customerPlantSelect').selectedIndex
    ]?.text || '';
    const customerAddress = document.getElementById('customerAddress').value.trim();
    const customerContact = document.getElementById('customerContact').value.trim();
    const customerPhone = document.getElementById('customerPhone').value.trim();
    const customerEmail = document.getElementById('customerEmail').value.trim();

    // 构建报告数据
    const reportData = {
        report_number: reportNumber,
        sample_number: sampleNumber,
        sample_type_id: parseInt(sampleTypeId),
        report_date: reportDate,
        sample_source: sampleSource,
        sampler: sampler,
        sampling_date: samplingDate,
        sampling_basis: samplingBasis,
        sample_received_date: sampleReceivedDate,
        sampling_location: samplingLocation,
        sample_status: sampleStatus,
        detection_date: detectionDate,
        product_standard: productStandard,
        test_conclusion: testConclusion,
        detection_items_description: testItems,
        additional_info: additionalInfo,
        detection_person: '',
        review_person: '',
        remark: JSON.stringify({
            customer_unit: customerUnit,
            customer_plant: customerPlant === '（无水厂名称）' ? '' : customerPlant,
            customer_address: customerAddress,
            customer_contact: customerContact,
            customer_phone: customerPhone,
            customer_email: customerEmail
        }), // 将客户信息存储在备注字段中
        review_status: 'draft',
        data: reportIndicators.map((ind, index) => ({
            indicator_id: ind.indicator_id,
            measured_value: ind.measured_value || '',
            remark: '',
            sort_order: index
        }))
    };

    try {
        const result = await apiRequest('/api/reports', {
            method: 'POST',
            body: JSON.stringify(reportData)
        });

        showToast('报告创建成功！报告编号: ' + result.report_number, 'success');

        // 重置表单
        resetNewReportForm();

    } catch (error) {
        console.error('保存报告失败:', error);
        showToast('保存报告失败: ' + error.message, 'error');
    }
}

// 重置表单
function resetNewReportForm() {
    document.getElementById('newReportSampleNumber').value = '';
    document.getElementById('newReportSampleType').value = '';

    // 重置客户信息
    document.getElementById('customerUnitInput').value = '';
    selectedUnit = '';
    document.getElementById('customerPlantSelect').value = '';
    document.getElementById('customerPlantSelect').disabled = true;
    document.getElementById('loadCustomerInfoBtn').disabled = true;
    document.getElementById('customerInfoFields').style.display = 'none';
    document.getElementById('customerAddress').value = '';
    document.getElementById('customerContact').value = '';
    document.getElementById('customerPhone').value = '';
    document.getElementById('customerEmail').value = '';

    document.getElementById('loadIndicatorsBtn').disabled = true;
    document.getElementById('indicatorsCard').style.display = 'none';

    reportIndicators = [];
    selectedCustomerId = null;

    // 重新设置默认值
    setNewReportDefaults();
}

// ==================== 从原始数据导入功能 ====================

// 打开原始数据导入模态框
function openRawDataImportModal() {
    const modal = new bootstrap.Modal(document.getElementById('rawDataImportModal'));
    const searchInput = document.getElementById('rawDataSearchInput');
    searchInput.value = '';
    document.getElementById('rawDataImportWarnings').style.display = 'none';
    // 初始加载列表
    searchRawDataSamples('');
    modal.show();
    setTimeout(() => searchInput.focus(), 300);
}

// 搜索原始数据样品编号
let rawDataSearchTimer = null;
async function searchRawDataSamples(keyword) {
    try {
        const url = '/api/raw-data/sample-numbers' + (keyword ? '?search=' + encodeURIComponent(keyword) : '');
        const results = await apiRequest(url);
        const tbody = document.getElementById('rawDataSearchResults');

        if (!results || results.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">未找到匹配的原始数据记录</td></tr>';
            return;
        }

        tbody.innerHTML = results.map(r => `
            <tr>
                <td>${escapeHtml(r.sample_number || '')}</td>
                <td>${escapeHtml(r.company_name || '')}</td>
                <td>${escapeHtml(r.plant_name || '')}</td>
                <td>${escapeHtml(r.sample_type || '')}</td>
                <td>${escapeHtml(r.sampling_date || '')}</td>
                <td>
                    <button class="btn btn-sm btn-success" onclick="selectRawDataForReport('${escapeHtml(r.sample_number || '')}')">
                        <i class="bi bi-check-lg"></i> 选择
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('搜索原始数据失败:', error);
    }
}

// 选择一条原始数据并导入到报告表单
async function selectRawDataForReport(sampleNumber) {
    try {
        const data = await apiRequest('/api/raw-data/for-report?sample_number=' + encodeURIComponent(sampleNumber));

        // 1. 填充样品编号
        document.getElementById('newReportSampleNumber').value = data.sample_number || '';

        // 2. 填充采样日期
        if (data.sampling_date) {
            document.getElementById('newSamplingDate').value = data.sampling_date;
        }

        // 3. 选择样品类型
        if (data.sample_type_id) {
            const sampleTypeSelect = document.getElementById('newReportSampleType');
            sampleTypeSelect.value = data.sample_type_id;
            // 触发change事件以启用加载按钮
            sampleTypeSelect.dispatchEvent(new Event('change'));
        }

        // 4. 填充客户信息（被检单位）
        if (data.company_name) {
            document.getElementById('customerUnitInput').value = data.company_name;
        }

        // 5. 加载检测项目并填入检测值
        if (data.sample_type_id) {
            // 先加载模板检测项目
            const indicators = await apiRequest(`/api/template-indicators?sample_type_id=${data.sample_type_id}`);

            if (indicators && indicators.length > 0) {
                // 建立原始数据检测值的映射（按指标名称）
                const rawValueMap = {};
                if (data.detection_items) {
                    data.detection_items.forEach(item => {
                        rawValueMap[item.indicator_name] = item.measured_value;
                    });
                }
                if (data.unmatched_items) {
                    data.unmatched_items.forEach(item => {
                        rawValueMap[item.indicator_name] = item.measured_value;
                    });
                }

                // 用模板指标填充，同时匹配原始数据检测值
                reportIndicators = indicators.map((ind, index) => ({
                    ...ind,
                    order: index,
                    measured_value: rawValueMap[ind.indicator_name] !== undefined
                        ? rawValueMap[ind.indicator_name]
                        : (ind.default_value || '')
                }));

                renderIndicatorsTable();
                document.getElementById('indicatorsCard').style.display = 'block';
            }
        }

        // 6. 显示未匹配项警告
        const warningsDiv = document.getElementById('rawDataImportWarnings');
        if (data.unmatched_items && data.unmatched_items.length > 0) {
            const unmatchedNames = data.unmatched_items.map(i => i.indicator_name).join('、');
            warningsDiv.innerHTML = `
                <div class="alert alert-warning mb-0">
                    <i class="bi bi-exclamation-triangle"></i>
                    <strong>以下原始数据项未匹配到系统指标（${data.unmatched_items.length}项）：</strong><br>
                    ${escapeHtml(unmatchedNames)}<br>
                    <small class="text-muted">这些项目的检测值未自动导入，如需要请手动添加。</small>
                </div>`;
            warningsDiv.style.display = 'block';
        } else {
            warningsDiv.style.display = 'none';
        }

        // 提示匹配情况
        if (!data.sample_type_id) {
            showToast(`样品类型"${data.sample_type || ''}"未匹配，请手动选择`, 'warning');
        }
        if (!data.company_id) {
            showToast(`公司"${data.company_name || ''}"未在系统中匹配`, 'info');
        }

        showToast('原始数据已导入，请检查并补充信息', 'success');

        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('rawDataImportModal'));
        if (modal) modal.hide();

    } catch (error) {
        console.error('导入原始数据失败:', error);
        showToast('导入原始数据失败: ' + error.message, 'error');
    }
}

// 初始化原始数据导入搜索事件
function initRawDataImport() {
    const importBtn = document.getElementById('importRawDataBtn');
    if (importBtn) {
        importBtn.addEventListener('click', openRawDataImportModal);
    }

    const searchInput = document.getElementById('rawDataSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(rawDataSearchTimer);
            rawDataSearchTimer = setTimeout(() => {
                searchRawDataSamples(this.value.trim());
            }, 300);
        });
    }
}

// 选择编辑页面的样品来源
function selectEditSampleSource(source) {
    const sourceInput = document.getElementById('editSampleSource');
    const sourceDropdown = document.getElementById('editSampleSourceDropdown');

    if (sourceInput) {
        sourceInput.value = source;
    }

    if (sourceDropdown) {
        sourceDropdown.classList.remove('show');
    }

    updateSampleSourceLabels('edit', source);
}

// 初始化编辑页面的样品来源下拉菜单
function initEditSampleSourceDropdown() {
    const sourceInput = document.getElementById('editSampleSource');
    const sourceDropdown = document.getElementById('editSampleSourceDropdown');

    if (!sourceInput || !sourceDropdown) return;

    // 点击输入框显示下拉菜单
    sourceInput.addEventListener('focus', function() {
        sourceDropdown.classList.add('show');
    });

    sourceInput.addEventListener('click', function() {
        sourceDropdown.classList.add('show');
    });

    // 点击外部区域关闭下拉菜单
    document.addEventListener('click', function(e) {
        if (!sourceInput.contains(e.target) && !sourceDropdown.contains(e.target)) {
            sourceDropdown.classList.remove('show');
        }
    });

    // 监听手动输入变化
    sourceInput.addEventListener('input', function() {
        updateSampleSourceLabels('edit', this.value.trim());
    });
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    // 检查是否在报告填写页面
    if (document.getElementById('newReportSampleNumber')) {
        initNewReportPage();
        initRawDataImport();
    }

    // 绑定编辑报告页面的按钮事件
    const saveEditBtn = document.getElementById('saveEditReportBtn');
    const submitEditBtn = document.getElementById('submitEditReportBtn');

    if (saveEditBtn) {
        saveEditBtn.addEventListener('click', () => saveEditReport(false));
    }

    if (submitEditBtn) {
        submitEditBtn.addEventListener('click', () => saveEditReport(true));
    }

    // 初始化编辑页面的样品来源下拉菜单
    initEditSampleSourceDropdown();
});

console.log('水质检测报告系统V2前端已加载');
