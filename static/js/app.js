// 水质检测报告系统 V2 - 前端JavaScript

// 全局状态
const AppState = {
    currentUser: null,
    sampleTypes: [],
    indicators: [],
    indicatorGroups: [],
    companies: [],
    reports: [],
    reportTemplates: []
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
    return date.toLocaleString('zh-CN');
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN');
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

    // 模板配置
    document.getElementById('configTemplateBtn')?.addEventListener('click', configTemplate);
    document.getElementById('exportTemplateBtn')?.addEventListener('click', exportTemplate);

    // 报告填写
    document.getElementById('reportTemplate')?.addEventListener('change', onReportTemplateChange);
    document.getElementById('reportSampleType').addEventListener('change', onSampleTypeChange);
    document.getElementById('reportForm').addEventListener('submit', submitReport);
    document.getElementById('saveDraftBtn')?.addEventListener('click', saveDraft);
    document.getElementById('downloadImportTemplateBtn')?.addEventListener('click', downloadImportTemplate);
    document.getElementById('importReportsBtn')?.addEventListener('click', showImportReportsModal);

    // 待提交报告
    document.getElementById('searchPendingBtn')?.addEventListener('click', loadPendingReports);
    document.getElementById('refreshPendingBtn')?.addEventListener('click', loadPendingReports);

    // 报告查询
    document.getElementById('searchReportBtn').addEventListener('click', searchReports);
    document.getElementById('refreshReportBtn').addEventListener('click', () => loadReports());

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
            } else if (targetId === '#review') {
                loadReviewReports();
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

        // 更新下拉框
        const selects = ['templateSampleType', 'reportSampleType'];
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
                                Excel应包含以下列：指标名称、单位、默认值、所属分组、排序、说明<br>
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

// ==================== 模板配置 ====================
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

    // 生成分组显示的HTML
    let indicatorCheckboxes = '';
    for (const [groupName, indicators] of Object.entries(groupedIndicators)) {
        indicatorCheckboxes += `
            <div class="mb-3">
                <h6 class="text-primary border-bottom pb-2">
                    <i class="bi bi-folder"></i> ${groupName}
                    <span class="badge bg-secondary">${indicators.length}项</span>
                </h6>
                <div class="ps-3">
        `;

        indicators.forEach(ind => {
            const checked = currentIds.includes(ind.id) ? 'checked' : '';
            const remarkText = ind.remark ? `<br><small class="text-muted">备注: ${ind.remark}</small>` : '';
            const limitText = ind.limit_value ? `<br><small class="text-info">限值: ${ind.limit_value}</small>` : '';

            indicatorCheckboxes += `
                <div class="form-check mb-2">
                    <input class="form-check-input" type="checkbox" value="${ind.id}" id="ind_${ind.id}" ${checked}>
                    <label class="form-check-label" for="ind_${ind.id}">
                        <strong>${ind.name}</strong> ${ind.unit ? '<span class="text-muted">(' + ind.unit + ')</span>' : ''}
                        ${limitText}
                        ${remarkText}
                    </label>
                </div>
            `;
        });

        indicatorCheckboxes += `
                </div>
            </div>
        `;
    }

    const modalHTML = `
        <div class="modal fade" id="configTemplateModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-wrench"></i> 配置检测项目
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-info mb-3">
                            <i class="bi bi-info-circle"></i>
                            选择该样品类型需要检测的项目。已按分组显示，包含限值和备注信息。
                        </div>
                        <div style="max-height: 500px; overflow-y: auto;">
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
}

async function saveTemplateConfig(sampleTypeId) {
    const checkboxes = document.querySelectorAll('#configTemplateModal .form-check-input:checked');
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

// ==================== 报告填写 ====================
async function onReportTemplateChange() {
    const templateId = document.getElementById('reportTemplate').value;
    const formContent = document.getElementById('reportFormContent');
    const templateFieldsArea = document.getElementById('templateFieldsArea');

    if (!templateId) {
        formContent.style.display = 'none';
        return;
    }

    try {
        // 加载模板字段配置
        const fields = await apiRequest(`/api/template-fields/${templateId}`);

        // 显示表单内容区域
        formContent.style.display = 'block';

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

        showToast(`已加载模板字段配置 (${fields.length}个字段)`);
    } catch (error) {
        console.error('加载模板字段失败:', error);
        showToast('加载模板字段失败', 'error');
        formContent.style.display = 'none';
    }
}

async function downloadImportTemplate() {
    const templateId = document.getElementById('reportTemplate').value;
    if (!templateId) {
        showToast('请先选择报告模板', 'warning');
        return;
    }

    try {
        const url = `/api/download-import-template?template_id=${templateId}`;
        window.location.href = url;
        showToast('导入模板下载中...');
    } catch (error) {
        showToast('下载失败', 'error');
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
        const result = await apiRequest('/api/reports', {
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
        document.getElementById('reportForm').reset();
        document.getElementById('reportDataArea').innerHTML = '<p class="text-muted">请先选择样品类型</p>';
        document.getElementById('reportFormContent').style.display = 'none';
        document.getElementById('templateFieldsArea').innerHTML = '';

        // 如果是草稿，刷新待提交报告列表
        if (reviewStatus === 'draft') {
            loadPendingReports();
        }
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
                <td>${formatDate(report.detection_date)}</td>
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
                                    <div class="report-info-value">${formatDate(report.detection_date)}</div>
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
        a.download = `report_${id}.${format === 'excel' ? 'xlsx' : 'docx'}`;
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
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">暂无备份</td></tr>';
        return;
    }

    backups.forEach(backup => {
        tbody.innerHTML += `
            <tr>
                <td>${backup.name}</td>
                <td>${formatDateTime(backup.backup_time)}</td>
                <td>
                    <button class="btn btn-sm btn-warning" onclick="restoreBackup('${backup.name}')">
                        <i class="bi bi-arrow-counterclockwise"></i> 恢复
                    </button>
                </td>
            </tr>
        `;
    });
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

            return `
                <tr>
                    <td>${report.report_number || '-'}</td>
                    <td>${report.sample_number || '-'}</td>
                    <td>${report.sample_type_name || '-'}</td>
                    <td>${report.company_name || '-'}</td>
                    <td>${report.template_name || '-'}</td>
                    <td>${statusBadge}</td>
                    <td>${new Date(report.created_at).toLocaleString('zh-CN')}</td>
                    <td class="text-truncate" style="max-width: 200px;" title="${rejectReason}">${rejectReason}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="submitPendingReport(${report.id})">
                            <i class="bi bi-send"></i> 提交审核
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

console.log('水质检测报告系统V2前端已加载');
