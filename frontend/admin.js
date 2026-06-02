const API = 'http://127.0.0.1:9000';

function getToken() { return localStorage.getItem('infraMind_access_token'); }

async function api(path, opts = {}) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const res = await fetch(API + path, { ...opts, headers });
    if (res.status === 401) { logout(); return null; }
    return res;
}

function logout() {
    ['infraMind_access_token','infraMind_refresh_token',
     'infraMind_session_name','infraMind_session_email','infraMind_session_id']
        .forEach(k => localStorage.removeItem(k));
    window.location.href = 'index.html';
}

function toast(msg, type = 'success') {
    const el = document.createElement('div');
    el.className = 'toast ' + type;
    el.innerHTML = type === 'success'
        ? `<svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>${msg}`
        : `<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>${msg}`;
    document.getElementById('toasts').appendChild(el);
    setTimeout(() => el.remove(), 3500);
}

function fmt(dt) {
    if (!dt) return '—';
    return new Date(dt).toLocaleDateString('pt-BR');
}

function statusBadge(s) {
    const map = { open:'badge-open', in_progress:'badge-prog', resolved:'badge-done', closed:'badge-closed' };
    const lbl = { open:'Aberta', in_progress:'Em andamento', resolved:'Resolvida', closed:'Fechada' };
    return `<span class="badge ${map[s]||'badge-closed'}">${lbl[s]||s}</span>`;
}

function impBadge(c) {
    if (!c) return '<span style="color:var(--text3);font-size:12px">—</span>';
    const map = { green:'badge-green', yellow:'badge-yellow', red:'badge-red' };
    const lbl = { green:'Normal', yellow:'Médio', red:'Importante' };
    return `<span class="badge ${map[c]}">${lbl[c]}</span>`;
}

// ── PAGE ROUTING ──
const pages = ['dashboard','occurrences','users','feedbacks','logs','categories','map'];
function showPage(id) {
    pages.forEach(p => {
        document.getElementById('page-'+p).classList.toggle('active', p === id);
        document.querySelectorAll('.nav-item').forEach(n => {
            if (n.getAttribute('onclick') === `showPage('${p}')`) n.classList.toggle('active', p === id);
        });
    });
    const titles = { dashboard:'Dashboard', occurrences:'Ocorrências', users:'Usuários', feedbacks:'Feedbacks', logs:'Logs de Auditoria', categories:'Categorias', map:'Mapa de Ocorrências' };
    document.getElementById('page-title').textContent = titles[id] || id;
    if (id === 'dashboard')   loadDashboard();
    if (id === 'occurrences') loadOccurrences();
    if (id === 'users')       loadUsers();
    if (id === 'feedbacks')   loadFeedbacks();
    if (id === 'logs')        loadLogs();
    if (id === 'categories')  loadCategories();
    if (id === 'map')         loadMapPage();
}

// ── MODAL ──
function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
document.querySelectorAll('.modal-backdrop').forEach(b => b.addEventListener('click', e => { if (e.target === b) b.classList.remove('open'); }));

// ── DATA CACHES ──
let allOcc = [], allUsers = [], allCats = [], allLogs = [], allFeedbacks = [];

// ── DASHBOARD ──
async function loadDashboard() {
    try {
        const [rStats, rOcc, rUsers] = await Promise.all([
            api('/api/v1/statistics/'),
            api('/api/v1/occurrences/'),
            api('/api/v1/users/')
        ]);
        if (!rStats || !rOcc || !rUsers) return;

        const stats = await rStats.json();
        const occData = await rOcc.json();
        const userData = await rUsers.json();
        const occs = Array.isArray(occData) ? occData : (occData.results || []);
        const users = Array.isArray(userData) ? userData : (userData.results || []);

        document.getElementById('s-users').textContent = stats.total_usuarios ?? users.length;
        document.getElementById('s-occ').textContent = stats.total_ocorrencias ?? occs.length;
        const resolved = occs.filter(o => o.status === 'resolved' || o.status === 'closed').length;
        const open = occs.filter(o => o.status === 'open').length;
        document.getElementById('s-resolved').textContent = resolved;
        document.getElementById('s-open').textContent = open;

        // mini chart
        const statusGroups = { open:0, in_progress:0, resolved:0, closed:0 };
        occs.forEach(o => { if (statusGroups[o.status] !== undefined) statusGroups[o.status]++; });
        const maxVal = Math.max(...Object.values(statusGroups), 1);
        const labels = { open:'Aberta', in_progress:'Andamento', resolved:'Resolvida', closed:'Fechada' };
        const colors = { open:'var(--accent)', in_progress:'var(--yellow)', resolved:'var(--green)', closed:'var(--text3)' };
        document.getElementById('status-chart').innerHTML = Object.entries(statusGroups).map(([k,v]) =>
            `<div class="bar-col">
                <div class="bar" style="height:${Math.round((v/maxVal)*44)}px;background:${colors[k]}"></div>
                <div class="bar-lbl">${v}</div>
                <div class="bar-lbl">${labels[k]}</div>
            </div>`
        ).join('');

        // cats
        const rCats = await api('/api/v1/categories/');
        const catData = await rCats.json();
        allCats = Array.isArray(catData) ? catData : (catData.results || []);
        const catCount = {};
        occs.forEach(o => { if (o.category) catCount[o.category] = (catCount[o.category]||0)+1; });
        document.getElementById('cat-list').innerHTML = allCats.slice(0,6).map(c =>
            `<div style="display:flex;align-items:center;gap:10px;font-size:13px;">
                <span style="flex:1;color:var(--text)">${c.name}</span>
                <span style="font-family:var(--mono);font-size:11px;color:var(--text3)">${catCount[c.id]||0} ocs</span>
                <span class="badge ${c.is_active ? 'badge-active' : 'badge-inactive'}" style="font-size:10px">${c.is_active?'Ativa':'Inativa'}</span>
            </div>`
        ).join('') || '<div style="color:var(--text3);font-size:13px">Nenhuma categoria</div>';

        // recent occs
        const recent = [...occs].sort((a,b) => new Date(b.created_at)-new Date(a.created_at)).slice(0,8);
        document.getElementById('recent-occ-tbody').innerHTML = recent.length
            ? recent.map(o => `<tr>
                <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${o.title}</td>
                <td>${statusBadge(o.status)}</td>
                <td><span style="font-family:var(--mono);font-size:12px;color:var(--text2)">${o.priority||0}</span></td>
                <td>${impBadge(o.importance_color)}</td>
                <td style="color:var(--text2);font-size:12px">${fmt(o.created_at)}</td>
            </tr>`).join('')
            : '<tr><td colspan="5" class="empty-state">Nenhuma ocorrência</td></tr>';

    } catch(e) { console.error(e); toast('Erro ao carregar dashboard','error'); }
}

// ── OCCURRENCES ──
let occPage = 1; const OCC_PER = 12;
async function loadOccurrences() {
    document.getElementById('occ-tbody').innerHTML = '<tr><td colspan="7" class="loading">Carregando...</td></tr>';
    try {
        const r = await api('/api/v1/occurrences/');
        if (!r) return;
        const data = await r.json();
        allOcc = Array.isArray(data) ? data : (data.results || []);
        occPage = 1;
        renderOcc();
    } catch(e) { toast('Erro ao carregar ocorrências','error'); }
}

function filterOcc() { occPage = 1; renderOcc(); }

function renderOcc() {
    const search = (document.getElementById('occ-search').value || '').toLowerCase();
    const sf = document.getElementById('occ-status-filter').value;
    const cf = document.getElementById('occ-color-filter').value;
    const filtered = allOcc.filter(o =>
        (!search || o.title.toLowerCase().includes(search)) &&
        (!sf || o.status === sf) &&
        (!cf || o.importance_color === cf)
    );
    const total = filtered.length;
    const start = (occPage-1)*OCC_PER;
    const slice = filtered.slice(start, start+OCC_PER);

    document.getElementById('occ-tbody').innerHTML = slice.length
        ? slice.map(o => `<tr>
            <td style="font-family:var(--mono);font-size:11px;color:var(--text3)">#${o.id}</td>
            <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${o.title}">${o.title}</td>
            <td>${statusBadge(o.status)}</td>
            <td>
                <div class="imp-selector">
                    ${['green','yellow','red'].map(c=>`<div class="imp-btn ${c}-btn${o.importance_color===c?' selected':''}" title="${c}" onclick="quickSetImportance(${o.id},'${c}',this)"></div>`).join('')}
                </div>
            </td>
            <td><span style="font-family:var(--mono);font-size:12px;color:var(--text2)">${o.validation_count||0}</span></td>
            <td style="color:var(--text2);font-size:12px">${fmt(o.created_at)}</td>
            <td>
                <div style="display:flex;gap:6px">
                    <button class="btn btn-ghost btn-sm" onclick="openOccModal(${o.id})">Editar</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteOcc(${o.id})">Del</button>
                </div>
            </td>
        </tr>`).join('')
        : '<tr><td colspan="7" class="empty-state">Nenhuma ocorrência encontrada</td></tr>';

    const pages = Math.ceil(total/OCC_PER);
    document.getElementById('occ-pagination').innerHTML =
        `<span class="pagination-info">${total} ocorrências — pág. ${occPage}/${pages||1}</span>
        <div class="pagination-btns">
            <button class="pg-btn" onclick="occPage=Math.max(1,occPage-1);renderOcc()">‹</button>
            ${Array.from({length:Math.min(pages,5)},(_,i)=>`<button class="pg-btn${i+1===occPage?' active':''}" onclick="occPage=${i+1};renderOcc()">${i+1}</button>`).join('')}
            <button class="pg-btn" onclick="occPage=Math.min(${pages||1},occPage+1);renderOcc()">›</button>
        </div>`;
}

async function quickSetImportance(id, color, btn) {
    const row = btn.closest('tr');
    row.querySelectorAll('.imp-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    try {
        const r = await api(`/api/v1/occurrences/${id}/`, { method:'PATCH', body: JSON.stringify({ importance_color: color }) });
        if (!r || !r.ok) { toast('Erro ao atualizar','error'); return; }
        const idx = allOcc.findIndex(o => o.id === id);
        if (idx !== -1) allOcc[idx].importance_color = color;
        toast('Importância atualizada');
    } catch(e) { toast('Erro de conexão','error'); }
}

function openOccModal(id) {
    const occ = allOcc.find(o => o.id === id);
    if (!occ) return;
    document.getElementById('edit-occ-id').value = id;
    document.getElementById('edit-occ-status').value = occ.status || 'open';
    document.getElementById('edit-occ-importance').value = occ.importance_color || '';
    document.getElementById('edit-occ-time').value = occ.estimated_time || '';
    openModal('occ-modal');
}

async function saveOcc() {
    const id = document.getElementById('edit-occ-id').value;
    const payload = {
        status: document.getElementById('edit-occ-status').value,
        importance_color: document.getElementById('edit-occ-importance').value || null,
        estimated_time: document.getElementById('edit-occ-time').value || null,
    };
    try {
        const r = await api(`/api/v1/occurrences/${id}/`, { method:'PATCH', body: JSON.stringify(payload) });
        if (!r || !r.ok) { toast('Erro ao salvar','error'); return; }
        closeModal('occ-modal');
        toast('Ocorrência atualizada');
        loadOccurrences();
    } catch(e) { toast('Erro de conexão','error'); }
}

async function deleteOcc(id) {
    if (!confirm('Excluir permanentemente esta ocorrência?')) return;
    try {
        await api(`/api/v1/occurrences/${id}/`, { method:'DELETE' });
        toast('Ocorrência removida');
        loadOccurrences();
    } catch(e) { toast('Erro ao excluir','error'); }
}

// ── USERS ──
let usersPage = 1; const USERS_PER = 12;
async function loadUsers() {
    document.getElementById('users-tbody').innerHTML = '<tr><td colspan="7" class="loading">Carregando...</td></tr>';
    try {
        const r = await api('/api/v1/users/');
        if (!r) return;
        const data = await r.json();
        allUsers = Array.isArray(data) ? data : (data.results || []);
        usersPage = 1;
        renderUsers();
    } catch(e) { toast('Erro ao carregar usuários','error'); }
}

function filterUsers() { usersPage = 1; renderUsers(); }

function renderUsers() {
    const search = (document.getElementById('user-search').value || '').toLowerCase();
    const tf = document.getElementById('user-type-filter').value;
    const filtered = allUsers.filter(u =>
        (!search || (u.username||'').toLowerCase().includes(search) || (u.email||'').toLowerCase().includes(search) || (u.first_name||'').toLowerCase().includes(search)) &&
        (!tf || u.user_type === tf)
    );
    const total = filtered.length;
    const start = (usersPage-1)*USERS_PER;
    const slice = filtered.slice(start, start+USERS_PER);
    const initials = u => ((u.first_name||u.username||'?')[0] + (u.last_name||'')[0]).toUpperCase().replace(/\s/,'');

    document.getElementById('users-tbody').innerHTML = slice.length
        ? slice.map(u => `<tr>
            <td style="font-family:var(--mono);font-size:11px;color:var(--text3)">#${u.id}</td>
            <td>
                <div style="display:flex;align-items:center;gap:8px">
                    <div class="avatar" style="width:28px;height:28px;font-size:10px">${initials(u)}</div>
                    <div>
                        <div style="font-size:13px">${u.first_name||''} ${u.last_name||''}</div>
                        <div style="font-size:11px;color:var(--text3);font-family:var(--mono)">@${u.username}</div>
                    </div>
                </div>
            </td>
            <td style="font-size:12px;color:var(--text2)">${u.email||'—'}</td>
            <td><span class="badge ${u.user_type==='admin'?'badge-admin':'badge-citizen'}">${u.user_type==='admin'?'Admin':'Cidadão'}</span></td>
            <td><span class="badge ${u.is_active?'badge-active':'badge-inactive'}">${u.is_active?'Ativo':'Inativo'}</span></td>
            <td style="font-size:12px;color:var(--text2)">${fmt(u.created_at)}</td>
            <td>
                <button class="btn btn-ghost btn-sm" onclick="openUserModal(${u.id})">Ver</button>
            </td>
        </tr>`).join('')
        : '<tr><td colspan="7" class="empty-state">Nenhum usuário encontrado</td></tr>';

    const pages = Math.ceil(total/USERS_PER);
    document.getElementById('users-pagination').innerHTML =
        `<span class="pagination-info">${total} usuários — pág. ${usersPage}/${pages||1}</span>
        <div class="pagination-btns">
            <button class="pg-btn" onclick="usersPage=Math.max(1,usersPage-1);renderUsers()">‹</button>
            ${Array.from({length:Math.min(pages,5)},(_,i)=>`<button class="pg-btn${i+1===usersPage?' active':''}" onclick="usersPage=${i+1};renderUsers()">${i+1}</button>`).join('')}
            <button class="pg-btn" onclick="usersPage=Math.min(${pages||1},usersPage+1);renderUsers()">›</button>
        </div>`;
}

function openUserModal(id) {
    const u = allUsers.find(x => x.id === id);
    if (!u) return;
    document.getElementById('user-modal-title').textContent = (u.first_name||u.username) + ' ' + (u.last_name||'');
    document.getElementById('user-modal-body').innerHTML = `
        <div class="detail-grid">
            <div class="detail-field"><label>Username</label><span>@${u.username}</span></div>
            <div class="detail-field"><label>E-mail</label><span>${u.email||'—'}</span></div>
            <div class="detail-field"><label>Telefone</label><span>${u.phone||'—'}</span></div>
            <div class="detail-field"><label>Tipo</label><span class="badge ${u.user_type==='admin'?'badge-admin':'badge-citizen'}">${u.user_type==='admin'?'Administrador':'Cidadão'}</span></div>
            <div class="detail-field"><label>Status</label><span class="badge ${u.is_active?'badge-active':'badge-inactive'}">${u.is_active?'Ativo':'Inativo'}</span></div>
            <div class="detail-field"><label>Cadastro</label><span>${fmt(u.created_at)}</span></div>
            <div class="detail-field" style="grid-column:1/-1"><label>Endereço</label><span>${u.address||'—'}</span></div>
        </div>`;
    document.getElementById('user-delete-btn').onclick = () => deleteUser(id);
    openModal('user-modal');
}

async function deleteUser(id) {
    if (!confirm('Excluir este usuário? Esta ação não pode ser desfeita.')) return;
    try {
        await api(`/api/v1/users/${id}/`, { method:'DELETE' });
        closeModal('user-modal');
        toast('Usuário removido');
        loadUsers();
    } catch(e) { toast('Erro ao excluir','error'); }
}

// ── FEEDBACKS ──
async function loadFeedbacks() {
    document.getElementById('feedback-list').innerHTML = '<div style="grid-column:1/-1" class="loading">Carregando...</div>';
    try {
        const r = await api('/api/v1/feedbacks/');
        if (!r) return;
        const data = await r.json();
        allFeedbacks = Array.isArray(data) ? data : (data.results || []);
        document.getElementById('feedback-count-badge').textContent = allFeedbacks.length || '0';

        if (!allFeedbacks.length) {
            document.getElementById('feedback-list').innerHTML = '<div style="grid-column:1/-1" class="empty-state">Nenhum feedback registrado</div>';
            return;
        }

        document.getElementById('feedback-list').innerHTML = allFeedbacks.map(f => {
            const stars = Array.from({length:5},(_,i)=>`<span class="star${i<f.rating?'':' empty'}">★</span>`).join('');
            return `<div class="feedback-card">
                <div class="feedback-meta">
                    <div class="avatar" style="width:30px;height:30px;font-size:11px">U${f.user}</div>
                    <span class="feedback-user">Usuário #${f.user}</span>
                    <span class="feedback-date">${fmt(f.created_at)}</span>
                </div>
                <div class="feedback-text">"${f.comment}"</div>
                <div class="feedback-footer">
                    <div class="stars">${stars}</div>
                    <span class="feedback-occ">Oc. #${f.occurrence} ${f.resolved?'<span class="badge badge-active" style="font-size:10px">Resolvida</span>':''}</span>
                </div>
            </div>`;
        }).join('');
    } catch(e) { toast('Erro ao carregar feedbacks','error'); }
}

// ── LOGS ──
let logsPage = 1; const LOGS_PER = 15;
async function loadLogs() {
    document.getElementById('logs-tbody').innerHTML = '<tr><td colspan="7" class="loading">Carregando...</td></tr>';
    try {
        const r = await api('/api/v1/logs/');
        if (!r) return;
        const data = await r.json();
        allLogs = Array.isArray(data) ? data : (data.results || []);
        logsPage = 1;
        renderLogs();
    } catch(e) { toast('Erro ao carregar logs','error'); }
}

function renderLogs() {
    const total = allLogs.length;
    const start = (logsPage-1)*LOGS_PER;
    const slice = allLogs.slice(start, start+LOGS_PER);
    const actionClass = { create:'log-create', update:'log-update', delete:'log-delete', validate:'log-validate', status_change:'log-status' };

    document.getElementById('logs-tbody').innerHTML = slice.length
        ? slice.map(l => `<tr>
            <td style="font-family:var(--mono);font-size:11px;color:var(--text3)">#${l.id}</td>
            <td style="font-size:12px;color:var(--text2)">${l.user ? '#'+l.user : '—'}</td>
            <td><span class="log-action ${actionClass[l.action]||''}">${l.action}</span></td>
            <td style="font-family:var(--mono);font-size:12px;color:var(--text2)">${l.model_name}</td>
            <td style="font-family:var(--mono);font-size:12px;color:var(--text3)">${l.object_id}</td>
            <td style="font-family:var(--mono);font-size:11px;color:var(--text3)">${l.ip_address||'—'}</td>
            <td style="font-size:12px;color:var(--text2)">${fmt(l.created_at)}</td>
        </tr>`).join('')
        : '<tr><td colspan="7" class="empty-state">Nenhum log encontrado</td></tr>';

    const pages = Math.ceil(total/LOGS_PER);
    document.getElementById('logs-pagination').innerHTML =
        `<span class="pagination-info">${total} logs — pág. ${logsPage}/${pages||1}</span>
        <div class="pagination-btns">
            <button class="pg-btn" onclick="logsPage=Math.max(1,logsPage-1);renderLogs()">‹</button>
            ${Array.from({length:Math.min(pages,5)},(_,i)=>`<button class="pg-btn${i+1===logsPage?' active':''}" onclick="logsPage=${i+1};renderLogs()">${i+1}</button>`).join('')}
            <button class="pg-btn" onclick="logsPage=Math.min(${pages||1},logsPage+1);renderLogs()">›</button>
        </div>`;
}

// ── CATEGORIES ──
async function loadCategories() {
    document.getElementById('cats-tbody').innerHTML = '<tr><td colspan="6" class="loading">Carregando...</td></tr>';
    try {
        const r = await api('/api/v1/categories/');
        if (!r) return;
        const data = await r.json();
        allCats = Array.isArray(data) ? data : (data.results || []);
        renderCats();
    } catch(e) { toast('Erro ao carregar categorias','error'); }
}

function renderCats() {
    document.getElementById('cats-tbody').innerHTML = allCats.length
        ? allCats.map(c => `<tr>
            <td style="font-family:var(--mono);font-size:11px;color:var(--text3)">#${c.id}</td>
            <td style="font-weight:500">${c.name}</td>
            <td style="color:var(--text2);font-size:13px">${c.description||'—'}</td>
            <td><span class="badge ${c.is_active?'badge-active':'badge-inactive'}">${c.is_active?'Ativa':'Inativa'}</span></td>
            <td style="font-size:12px;color:var(--text2)">${fmt(c.created_at)}</td>
            <td>
                <div style="display:flex;gap:6px">
                    <button class="btn btn-ghost btn-sm" onclick="openCatModal(${c.id})">Editar</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteCat(${c.id})">Del</button>
                </div>
            </td>
        </tr>`).join('')
        : '<tr><td colspan="6" class="empty-state">Nenhuma categoria</td></tr>';
}

function openCatModal(id) {
    const cat = id ? allCats.find(c => c.id === id) : null;
    document.getElementById('cat-modal-title').textContent = cat ? 'Editar Categoria' : 'Nova Categoria';
    document.getElementById('cat-id').value = id || '';
    document.getElementById('cat-name').value = cat ? cat.name : '';
    document.getElementById('cat-desc').value = cat ? (cat.description||'') : '';
    document.getElementById('cat-active').value = cat ? String(cat.is_active) : 'true';
    openModal('cat-modal');
}

async function saveCat() {
    const id = document.getElementById('cat-id').value;
    const payload = {
        name: document.getElementById('cat-name').value.trim(),
        description: document.getElementById('cat-desc').value.trim() || null,
        is_active: document.getElementById('cat-active').value === 'true',
    };
    if (!payload.name) { toast('Nome é obrigatório','error'); return; }
    try {
        const r = id
            ? await api(`/api/v1/categories/${id}/`, { method:'PUT', body: JSON.stringify(payload) })
            : await api('/api/v1/categories/', { method:'POST', body: JSON.stringify(payload) });
        if (!r || !r.ok) { toast('Erro ao salvar categoria','error'); return; }
        closeModal('cat-modal');
        toast(id ? 'Categoria atualizada' : 'Categoria criada');
        loadCategories();
    } catch(e) { toast('Erro de conexão','error'); }
}

async function deleteCat(id) {
    if (!confirm('Excluir esta categoria?')) return;
    try {
        await api(`/api/v1/categories/${id}/`, { method:'DELETE' });
        toast('Categoria removida');
        loadCategories();
    } catch(e) { toast('Erro ao excluir','error'); }
}

// ── GLOBAL SEARCH ──
function onGlobalSearch(v) {
    const cur = document.querySelector('.page.active').id.replace('page-','');
    if (cur === 'occurrences') { document.getElementById('occ-search').value = v; filterOcc(); }
    if (cur === 'users') { document.getElementById('user-search').value = v; filterUsers(); }
}

// ── INIT ──
async function init() {
    if (!getToken()) { window.location.href = 'index.html'; return; }
    const token = getToken();
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const uid = payload.user_id;
        const r = await api('/api/v1/users/');
        if (r) {
            const data = await r.json();
            const users = Array.isArray(data) ? data : (data.results || []);
            const me = users.find(u => u.id === uid);
            if (me) {
                const name = (me.first_name && me.last_name) ? `${me.first_name} ${me.last_name}` : me.username;
                document.getElementById('admin-name').textContent = name;
                document.getElementById('admin-avatar').textContent = name.slice(0,2).toUpperCase();
            }
        }
    } catch(e) {}
    loadDashboard();
}

// ============================================================
// MAPA DE OCORRÊNCIAS — RF26
// Cole este bloco no FINAL do seu admin.js
// Dependência: Leaflet.js (adicionada automaticamente no loadMapPage)
// ============================================================

// ── Estado do mapa ──────────────────────────────────────────
let _mapInstance   = null;   // instância Leaflet
let _mapMarkers    = [];     // todos os markers renderizados
let _mapOccData    = [];     // ocorrências com coordenadas válidas
let _catColorMap   = {};     // { category_id: '#hexcolor' }
let _leafletLoaded = false;

// Paleta de cores para categorias (atribuída na ordem de chegada)
const CAT_COLORS = [
    '#4f6ef7', // azul  (accent)
    '#22c55e', // verde
    '#f59e0b', // amarelo
    '#ef4444', // vermelho
    '#a855f7', // roxo
    '#06b6d4', // ciano
    '#f97316', // laranja
    '#ec4899', // rosa
    '#84cc16', // lima
    '#14b8a6', // teal
    '#8b5cf6', // violeta
    '#f43f5e', // rose
];

// ── Rótulos de status ────────────────────────────────────────
const STATUS_LABEL = {
    open:        'Aberta',
    in_progress: 'Em Andamento',
    resolved:    'Resolvida',
    closed:      'Fechada',
};

const IMPORTANCE_LABEL = {
    green:  '🟢 Normal',
    yellow: '🟡 Médio',
    red:    '🔴 Importante',
};

// ── Carrega Leaflet dinamicamente (evita dependência no HTML) ─
function loadLeaflet() {
    return new Promise(resolve => {
        if (_leafletLoaded || window.L) { _leafletLoaded = true; resolve(); return; }

        const css  = document.createElement('link');
        css.rel    = 'stylesheet';
        css.href   = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(css);

        const script  = document.createElement('script');
        script.src    = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
        script.onload = () => { _leafletLoaded = true; resolve(); };
        document.head.appendChild(script);
    });
}

// ── Ponto de entrada: chamado pelo showPage('map') ───────────
async function loadMapPage() {
    await loadLeaflet();

    // Garante que o container está visível antes de inicializar o mapa
    await new Promise(r => setTimeout(r, 50));

    try {
        // Busca ocorrências e categorias em paralelo
        const [rOcc, rCat] = await Promise.all([
            api('/api/v1/occurrences/'),
            api('/api/v1/categories/'),
        ]);

        const occData = await rOcc.json();
        const catData = await rCat.json();
        const allOccs = Array.isArray(occData) ? occData : (occData.results || []);
        const cats    = Array.isArray(catData) ? catData : (catData.results || []);

        // Armazena no cache global (reutiliza se já carregado)
        allCats = cats;

        // Filtra apenas ocorrências com coordenadas válidas
        _mapOccData = allOccs.filter(o =>
            o.latitude  != null && o.latitude  !== '' &&
            o.longitude != null && o.longitude !== '' &&
            !isNaN(parseFloat(o.latitude)) &&
            !isNaN(parseFloat(o.longitude))
        );

        // Atribui uma cor para cada categoria
        cats.forEach((cat, i) => {
            _catColorMap[cat.id] = CAT_COLORS[i % CAT_COLORS.length];
        });

        // Popula o select de categorias
        const catSel = document.getElementById('map-cat-filter');
        catSel.innerHTML = '<option value="">Todas as categorias</option>';
        cats.forEach(cat => {
            const opt = document.createElement('option');
            opt.value       = cat.id;
            opt.textContent = cat.name;
            catSel.appendChild(opt);
        });

        // Renderiza a legenda
        _renderLegend(cats);

        // Inicializa ou reinicializa o mapa
        _initMap();
        _renderMarkers(_mapOccData);

    } catch(e) {
        console.error('[InfraMind Map]', e);
        toast('Erro ao carregar mapa', 'error');
    }
}

// ── Inicializa o mapa Leaflet ────────────────────────────────
function _initMap() {
    const container = document.getElementById('map-container');

    // Destroi instância anterior (evita erro "already initialized")
    if (_mapInstance) {
        _mapInstance.remove();
        _mapInstance = null;
    }

    // Centro padrão: Brasil
    _mapInstance = L.map('map-container', {
        center: [-15.7801, -47.9292],
        zoom: 4,
        zoomControl: true,
    });

    // Tile escuro compatível com o tema dark do admin
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '© <a href="https://carto.com/">CARTO</a>',
        maxZoom: 19,
    }).addTo(_mapInstance);
}

// ── Renderiza markers no mapa ────────────────────────────────
function _renderMarkers(occs) {
    if (!_mapInstance) return;

    // Remove markers antigos
    _mapMarkers.forEach(m => _mapInstance.removeLayer(m));
    _mapMarkers = [];

    if (!occs.length) {
        document.getElementById('map-count-label').textContent = '0 ocorrências';
        return;
    }

    const bounds = [];

    occs.forEach(occ => {
        const lat  = parseFloat(occ.latitude);
        const lng  = parseFloat(occ.longitude);
        const color = _catColorMap[occ.category] || '#4f6ef7';

        // SVG circle marker colorido por categoria
        const icon = L.divIcon({
            className: '',
            html: `
                <div style="
                    width:14px;height:14px;
                    border-radius:50%;
                    background:${color};
                    border:2px solid rgba(255,255,255,.35);
                    box-shadow:0 0 6px ${color}88;
                    cursor:pointer;
                "></div>`,
            iconSize:   [14, 14],
            iconAnchor: [7, 7],
        });

        const marker = L.marker([lat, lng], { icon });

        // Popup ao clicar no marker
        marker.on('click', (e) => _showPopup(occ, e.originalEvent));

        marker.addTo(_mapInstance);
        _mapMarkers.push(marker);
        bounds.push([lat, lng]);
    });

    // Ajusta o zoom para mostrar todos os pontos
    if (bounds.length > 0) {
        _mapInstance.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
    }

    document.getElementById('map-count-label').textContent =
        `${occs.length} ocorrência${occs.length !== 1 ? 's' : ''} no mapa`;
}

// ── Popup de detalhes ────────────────────────────────────────
function _showPopup(occ, mouseEvent) {
    const popup = document.getElementById('map-popup');
    const cat   = allCats.find(c => c.id === occ.category);
    const color = _catColorMap[occ.category] || '#4f6ef7';

    document.getElementById('popup-title').textContent = occ.title;
    document.getElementById('popup-body').innerHTML = `
        <div style="display:flex;align-items:center;gap:6px;">
            <span style="width:10px;height:10px;border-radius:50%;background:${color};flex-shrink:0"></span>
            <span>${cat ? cat.name : '—'}</span>
        </div>
        <div><span style="color:var(--text3)">Status:</span> ${STATUS_LABEL[occ.status] || occ.status}</div>
        ${occ.address ? `<div><span style="color:var(--text3)">Endereço:</span> ${occ.address}</div>` : ''}
        ${occ.importance_color ? `<div><span style="color:var(--text3)">Importância:</span> ${IMPORTANCE_LABEL[occ.importance_color] || occ.importance_color}</div>` : ''}
        <div><span style="color:var(--text3)">Validações:</span> ${occ.validation_count || 0}</div>
        <div><span style="color:var(--text3)">Data:</span> ${fmt(occ.created_at)}</div>
    `;

    // Posiciona o popup perto do clique
    const px = mouseEvent.clientX;
    const py = mouseEvent.clientY;
    const vpW = window.innerWidth;
    const vpH = window.innerHeight;
    popup.style.display = 'block';
    const pw = popup.offsetWidth  || 280;
    const ph = popup.offsetHeight || 160;
    popup.style.left = (px + pw + 20 > vpW ? px - pw - 10 : px + 16) + 'px';
    popup.style.top  = (py + ph + 20 > vpH ? py - ph - 10 : py + 16) + 'px';
}

// Fecha o popup ao clicar fora
document.addEventListener('click', e => {
    const popup = document.getElementById('map-popup');
    if (popup && !popup.contains(e.target) && popup.style.display !== 'none') {
        popup.style.display = 'none';
    }
});

// ── Legenda de categorias ────────────────────────────────────
function _renderLegend(cats) {
    const legend = document.getElementById('map-legend');
    if (!legend) return;
    legend.innerHTML = cats.map(cat => {
        const color = _catColorMap[cat.id] || '#4f6ef7';
        return `
            <div style="display:flex;align-items:center;gap:5px;font-size:12px;color:var(--text2);
                        background:var(--bg3);border:1px solid var(--border);border-radius:6px;
                        padding:3px 8px;cursor:pointer;"
                 onclick="quickFilterByCategory('${cat.id}')"
                 title="Filtrar por ${cat.name}">
                <span style="width:9px;height:9px;border-radius:50%;background:${color};flex-shrink:0"></span>
                ${cat.name}
            </div>`;
    }).join('');
}

// Clique na legenda → filtra direto por aquela categoria
function quickFilterByCategory(catId) {
    document.getElementById('map-cat-filter').value = catId;
    applyMapFilters();
}

// ── Filtros ──────────────────────────────────────────────────
function applyMapFilters() {
    const catFilter    = document.getElementById('map-cat-filter').value;
    const statusFilter = document.getElementById('map-status-filter').value;
    const impFilter    = document.getElementById('map-importance-filter').value;

    const filtered = _mapOccData.filter(o =>
        (!catFilter    || String(o.category)         === String(catFilter)) &&
        (!statusFilter || o.status                   === statusFilter) &&
        (!impFilter    || o.importance_color         === impFilter)
    );

    _renderMarkers(filtered);
}

function resetMapFilters() {
    document.getElementById('map-cat-filter').value        = '';
    document.getElementById('map-status-filter').value     = '';
    document.getElementById('map-importance-filter').value = '';
    _renderMarkers(_mapOccData);
}

init();