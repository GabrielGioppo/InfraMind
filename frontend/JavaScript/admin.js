// ============================================================
// ADMIN DASHBOARD — InfraMind 
// ============================================================
const API = 'http://127.0.0.1:9000';

// Mesmas chaves de sessão usadas por index.js / landing.js (im_access, im_refresh, im_user).
function getToken() { return localStorage.getItem('im_access'); }
function getRefresh() { return localStorage.getItem('im_refresh'); }

async function refreshToken() {
    const ref = getRefresh();
    if (!ref) return false;
    try {
        const r = await fetch(API + '/authentication/token/refresh/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh: ref })
        });
        if (!r.ok) return false;
        const d = await r.json();
        localStorage.setItem('im_access', d.access);
        if (d.refresh) localStorage.setItem('im_refresh', d.refresh);
        return true;
    } catch { return false; }
}

async function api(path, opts = {}) {
    const doFetch = () => {
        const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
        const token = getToken();
        if (token) headers['Authorization'] = 'Bearer ' + token;
        return fetch(API + path, { ...opts, headers });
    };
    let res = await doFetch();
    if (res.status === 401) {
        // Access token expirado (60 min): tenta renovar com o refresh token antes de deslogar.
        if (await refreshToken()) {
            res = await doFetch();
        } else {
            logout();
            return null;
        }
    }
    return res;
}

function logout() {
    ['im_access', 'im_refresh', 'im_user',
     // chaves antigas, de versões anteriores do painel
     'infraMind_access_token', 'infraMind_refresh_token',
     'infraMind_session_name', 'infraMind_session_email', 'infraMind_session_id']
        .forEach(k => localStorage.removeItem(k));
    window.location.href = 'landing.html';
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

function esc(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
}

// Data "pura" (YYYY-MM-DD, como vem do campo prazo_definido): formata sem passar por Date,
// que deslocaria o dia pelo fuso horário.
function fmtDay(d) {
    if (!d) return '—';
    const [y, m, dd] = String(d).slice(0, 10).split('-');
    return `${dd}/${m}/${y}`;
}

function fmtDateTime(dt) {
    if (!dt) return '—';
    return new Date(dt).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

// Prazo (SLA): data limite efetiva (sla_deadline) com a cor indicando a situação (sla_status)
function slaBadge(o) {
    if (!o.sla_deadline) return '<span style="color:var(--text3);font-size:12px">Sem prazo</span>';
    const map = {
        estourado: ['badge-red',    ' · atrasado'],
        proximo:   ['badge-yellow', ' · próximo'],
        ok:        ['badge-green',  ''],
    };
    const m = map[o.sla_status] || ['badge-closed', ' · concluída'];   // sla_status vazio = já encerrada
    const dia = fmt(o.sla_deadline);
    return `<span class="badge ${m[0]}" title="Limite: ${dia}">${dia}${m[1]}</span>`;
}

// Prioridade (cor de importância) como círculo colorido
function prioDot(o) {
    const lbl = { green:'Normal', yellow:'Médio', red:'Importante' };
    const c = lbl[o.importance_color] ? o.importance_color : 'none';
    const tip = c === 'none'
        ? 'Importância ainda não definida'
        : `Importância: ${lbl[c]} · pontuação ${o.priority || 0}`;
    return `<span class="prio-dot ${c}" title="${tip}"></span>`;
}

function rowClick(ev, id) {
    if (ev.target.closest('button, .imp-selector')) return;  // botões da linha têm ação própria
    openOccDetail(id);
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

        const atrasadas = occs.filter(o => o.sla_status === 'estourado').length;
        const alerta = document.getElementById('sla-alert');
        if (alerta) {
            alerta.style.display = atrasadas ? 'flex' : 'none';
            document.getElementById('sla-alert-text').textContent =
                `${atrasadas} ocorrência${atrasadas > 1 ? 's' : ''} com prazo (SLA) estourado${atrasadas > 1 ? 's' : ''}.`;
        }

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
            ? recent.map(o => `<tr class="row-link" onclick="openOccDetail(${o.id})">
                <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(o.title)}</td>
                <td>${statusBadge(o.status)}</td>
                <td>${prioDot(o)}</td>
                <td>${slaBadge(o)}</td>
                <td style="color:var(--text2);font-size:12px">${fmt(o.created_at)}</td>
            </tr>`).join('')
            : '<tr><td colspan="5" class="empty-state">Nenhuma ocorrência</td></tr>';

    } catch(e) { console.error(e); toast('Erro ao carregar dashboard','error'); }
}

// ── OCCURRENCES ──
let occPage = 1; const OCC_PER = 12;
async function loadOccurrences() {
    document.getElementById('occ-tbody').innerHTML = '<tr><td colspan="8" class="loading">Carregando...</td></tr>';
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
        ? slice.map(o => `<tr class="row-link" onclick="rowClick(event,${o.id})">
            <td style="font-family:var(--mono);font-size:11px;color:var(--text3)">#${o.id}</td>
            <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(o.title)}">${esc(o.title)}</td>
            <td>${statusBadge(o.status)}</td>
            <td>
                <div class="imp-selector">
                    ${['green','yellow','red'].map(c=>`<div class="imp-btn ${c}-btn${o.importance_color===c?' selected':''}" title="${c}" onclick="quickSetImportance(${o.id},'${c}',this)"></div>`).join('')}
                </div>
            </td>
            <td>${slaBadge(o)}</td>
            <td><span style="font-family:var(--mono);font-size:12px;color:var(--text2)">${o.validation_count||0}</span></td>
            <td style="color:var(--text2);font-size:12px">${fmt(o.created_at)}</td>
            <td>
                <div style="display:flex;gap:6px">
                    <button class="btn btn-ghost btn-sm" onclick="openOccDetail(${o.id})">Ver</button>
                    <button class="btn btn-ghost btn-sm" onclick="openOccModal(${o.id})">Editar</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteOcc(${o.id})">Del</button>
                </div>
            </td>
        </tr>`).join('')
        : '<tr><td colspan="8" class="empty-state">Nenhuma ocorrência encontrada</td></tr>';

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

async function openOccModal(id) {
    let occ = allOcc.find(o => o.id === id);
    if (!occ) {  // vindo do dashboard/mapa, a lista pode não estar carregada
        try {
            const r = await api(`/api/v1/occurrences/${id}/`);
            if (r && r.ok) occ = await r.json();
        } catch (e) { console.error(e); }
    }
    if (!occ) { toast('Ocorrência não encontrada', 'error'); return; }

    _reopenDetailAfterSave = document.getElementById('occ-detail-modal').classList.contains('open');
    closeModal('occ-detail-modal');

    document.getElementById('edit-occ-id').value = id;
    document.getElementById('edit-occ-name').textContent = `#${occ.id} · ${occ.title}`;
    document.getElementById('edit-occ-status').value = occ.status || 'open';
    document.getElementById('edit-occ-importance').value = occ.importance_color || '';
    document.getElementById('edit-occ-deadline').value = occ.prazo_definido || '';
    document.getElementById('edit-occ-feedback').value = '';
    document.getElementById('edit-occ-time').value = occ.estimated_time || '';
    document.getElementById('edit-occ-deadline-hint').textContent = occ.prazo_definido
        ? `Prazo atual: ${fmtDay(occ.prazo_definido)}. Escolha outra data para reajustar.`
        : (occ.sla_deadline
            ? `Sem data definida; hoje o prazo vem do tempo estimado (${fmt(occ.sla_deadline)}). Escolha uma data no calendário para substituí-lo.`
            : 'Sem prazo definido. Escolha uma data no calendário.');
    openModal('occ-modal');
}

let _reopenDetailAfterSave = false;

async function saveOcc() {
    const id = Number(document.getElementById('edit-occ-id').value);
    const payload = {
        status: document.getElementById('edit-occ-status').value,
        importance_color: document.getElementById('edit-occ-importance').value || null,
        estimated_time: document.getElementById('edit-occ-time').value || null,
        prazo_definido: document.getElementById('edit-occ-deadline').value || null,
    };
    const comment = document.getElementById('edit-occ-feedback').value.trim();
    try {
        const r = await api(`/api/v1/occurrences/${id}/`, { method:'PATCH', body: JSON.stringify(payload) });
        if (!r || !r.ok) {
            let msg = 'Erro ao salvar';
            try { msg += ': ' + JSON.stringify(await r.json()); } catch (e) {}
            toast(msg, 'error');
            return;
        }
        let feedbackFailed = false;
        if (comment) {
            const rf = await api('/api/v1/feedbacks/', { method:'POST', body: JSON.stringify({ occurrence: id, comment }) });
            feedbackFailed = !rf || !rf.ok;
        }
        closeModal('occ-modal');
        if (feedbackFailed) toast('Ocorrência salva, mas a atualização para o cidadão não foi enviada', 'error');
        else toast(comment ? 'Ocorrência atualizada e cidadão informado' : 'Ocorrência atualizada');
        await refreshAfterOccChange(id);
    } catch(e) { toast('Erro de conexão','error'); }
}

// Recarrega a tela que está aberta e, se o usuário veio do detalhe, volta para ele
async function refreshAfterOccChange(id) {
    const active = (document.querySelector('.page.active')?.id || '').replace('page-', '');
    if (active === 'occurrences') await loadOccurrences();
    else if (active === 'dashboard') loadDashboard();
    else if (active === 'map') loadMapPage();
    if (_reopenDetailAfterSave) { _reopenDetailAfterSave = false; openOccDetail(id); }
}

// ── DETALHE DA OCORRÊNCIA (somente leitura) ──
let _detailMap = null;
const URGENCY_LABEL = { critica:'Crítica', alta:'Alta', media:'Média', baixa:'Baixa' };

function imgSrc(raw) {
    if (!raw) return null;
    return raw.startsWith('http') ? raw : API + raw;
}

async function openOccDetail(id) {
    const body = document.getElementById('occ-detail-body');
    if (_detailMap) { _detailMap.remove(); _detailMap = null; }
    document.getElementById('occ-detail-title').textContent = `Ocorrência #${id}`;
    document.getElementById('occ-detail-edit-btn').onclick = () => openOccModal(id);
    body.innerHTML = '<div class="loading">Carregando...</div>';
    openModal('occ-detail-modal');

    try {
        const [r, rh] = await Promise.all([
            api(`/api/v1/occurrences/${id}/`),
            api(`/api/v1/occurrences/${id}/history/`),
        ]);
        if (!r) return;
        if (!r.ok) { body.innerHTML = '<div class="empty-state">Ocorrência não encontrada</div>'; return; }
        const o = await r.json();
        let hist = [];
        if (rh && rh.ok) { const d = await rh.json(); hist = Array.isArray(d) ? d : (d.results || []); }

        const img = o.images?.length ? imgSrc(o.images[0].image || o.images[0].url) : null;
        const lat = parseFloat(o.latitude), lng = parseFloat(o.longitude);
        const hasCoords = !isNaN(lat) && !isNaN(lng);
        const reporter = o.user_details?.username ? '@' + o.user_details.username : 'Anônimo';
        const urg = o.urgency_level
            ? `${URGENCY_LABEL[o.urgency_level] || o.urgency_level}${o.urgency_score ? ` (${o.urgency_score}/100)` : ''}`
            : '—';

        const notes = (o.feedbacks || []).map(f => {
            const official = !f.rating;
            const who = esc(f.user_details?.username || `Usuário #${f.user}`);
            const tag = official
                ? '<span class="badge badge-admin">Atualização oficial</span>'
                : `<span class="badge badge-citizen">Cidadão · ${'★'.repeat(f.rating)}</span>`;
            return `<div class="od-note">
                <div class="od-note-head"><span>${who} ${tag}</span><span class="od-note-date">${fmtDateTime(f.created_at)}</span></div>
                <p>${esc(f.comment)}</p>
            </div>`;
        }).join('') || '<div style="color:var(--text3);font-size:13px">Nenhuma atualização enviada ainda.</div>';

        const timeline = hist.map(h => {
            const text = h.change_type === 'status'
                ? `${statusBadge(h.previous_status || '—')} → ${statusBadge(h.new_status || '—')}`
                : '';
            const obs = h.observation ? `<span>${esc(h.observation)}</span>` : '';
            return `<div class="od-tl-item">
                <div class="od-tl-date">${fmtDateTime(h.changed_at)}</div>
                <div class="od-tl-text">${text}${obs}</div>
            </div>`;
        }).join('') || '<div style="color:var(--text3);font-size:13px">Sem alterações registradas.</div>';

        body.innerHTML = `
            ${img ? `<img class="od-hero" src="${img}" alt="" onerror="this.style.display='none'">` : ''}
            <div style="font-size:16px;font-weight:600;margin-bottom:4px">${esc(o.title)}</div>
            <div style="font-size:12px;color:var(--text3);margin-bottom:16px">Registrada em ${fmtDateTime(o.created_at)}</div>
            <div class="detail-grid">
                <div class="detail-field"><label>Status</label>${statusBadge(o.status)}</div>
                <div class="detail-field"><label>Importância</label>${impBadge(o.importance_color)}</div>
                <div class="detail-field"><label>Prazo</label>${slaBadge(o)}</div>
                <div class="detail-field"><label>Urgência (IA)</label><span>${esc(urg)}</span></div>
                <div class="detail-field"><label>Categoria</label><span>${esc(o.category_details?.name || '—')}</span></div>
                <div class="detail-field"><label>Cidadão</label><span>${esc(reporter)}</span></div>
                <div class="detail-field"><label>Validações</label><span>${o.validation_count || 0} confirmação(ões)</span></div>
                <div class="detail-field"><label>Tempo estimado</label><span>${o.estimated_time ? o.estimated_time + ' h' : '—'}</span></div>
                <div class="detail-field" style="grid-column:1/-1"><label>Endereço</label><span>${esc(o.address || '—')}</span></div>
            </div>
            <div class="od-section"><div class="od-section-title">Descrição</div>
                <div class="od-desc">${esc(o.description || '—')}</div></div>
            ${o.urgency_reason ? `<div class="od-section"><div class="od-section-title">Análise da IA</div>
                <div class="od-desc">${esc(o.urgency_reason)}</div></div>` : ''}
            ${hasCoords ? `<div class="od-section"><div class="od-section-title">Localização</div>
                <div id="occ-detail-map" class="od-map"></div></div>` : ''}
            <div class="od-section"><div class="od-section-title">Atualizações e feedbacks</div>${notes}</div>
            <div class="od-section"><div class="od-section-title">Histórico</div><div class="od-tl">${timeline}</div></div>
        `;

        if (hasCoords) {
            await loadLeaflet();
            if (!document.getElementById('occ-detail-map')) return;  // o modal foi fechado/trocado
            _detailMap = L.map('occ-detail-map').setView([lat, lng], 16);
            L.tileLayer(OSM_TILES, { attribution: OSM_ATTRIBUTION, maxZoom: 19, className: 'dark-tiles' }).addTo(_detailMap);
            L.circleMarker([lat, lng], { radius: 8, color: '#fff', weight: 2, fillColor: '#4f6ef7', fillOpacity: 1 }).addTo(_detailMap);
            setTimeout(() => _detailMap && _detailMap.invalidateSize(), 150);
        }
    } catch (e) {
        console.error(e);
        body.innerHTML = '<div class="empty-state">Erro ao carregar a ocorrência</div>';
    }
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
    const initials = u => {
        const f = (u.first_name || '').trim(), l = (u.last_name || '').trim();
        if (f && l) return (f[0] + l[0]).toUpperCase();
        return (f || u.username || '?').slice(0, 2).toUpperCase();
    };
    const fullName = u => [u.first_name, u.last_name].filter(Boolean).join(' ') || u.username;

    document.getElementById('users-tbody').innerHTML = slice.length
        ? slice.map(u => `<tr>
            <td style="font-family:var(--mono);font-size:11px;color:var(--text3)">#${u.id}</td>
            <td>
                <div style="display:flex;align-items:center;gap:8px">
                    <div class="avatar" style="width:28px;height:28px;font-size:10px">${initials(u)}</div>
                    <div>
                        <div style="font-size:13px">${esc(fullName(u))}</div>
                        <div style="font-size:11px;color:var(--text3);font-family:var(--mono)">@${esc(u.username)}</div>
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
    const actionClass = { create:'log-create', update:'log-update', delete:'log-delete', validate:'log-validate', status_change:'log-status', notification_sent:'log-create', notification_failed:'log-delete' };

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
    if (!getToken()) { window.location.href = 'landing.html'; return; }

    // Valida o token e o perfil: só administradores acessam este painel.
    let me = null;
    let loaded = false;
    try {
        const payload = JSON.parse(atob(getToken().split('.')[1]));
        const r = await api('/api/v1/users/');
        if (!r) return; // sessão inválida: api() já deslogou e redirecionou
        const data = await r.json();
        const users = Array.isArray(data) ? data : (data.results || []);
        me = users.find(u => u.id === payload.user_id) || null;
        loaded = true;
    } catch (e) { console.error(e); }

    // API fora do ar: não redireciona (evita loop index <-> admin), só avisa.
    if (!loaded) {
        document.body.insertAdjacentHTML('afterbegin',
            '<div style="padding:12px 16px;background:#3d1214;color:#f85149;font:500 .85rem sans-serif">' +
            'Não foi possível conectar à API. Verifique se o backend está rodando e recarregue a página.</div>');
        return;
    }

    if (!me || !(me.user_type === 'admin' || me.is_staff)) {
        window.location.href = 'index.html';
        return;
    }

    const name = (me.first_name && me.last_name) ? `${me.first_name} ${me.last_name}` : me.username;
    document.getElementById('admin-name').textContent = name;
    document.getElementById('admin-avatar').textContent = name.slice(0, 2).toUpperCase();

    loadDashboard();
    loadNotifications();
}

// ============================================================
// NOTIFICAÇÕES (UC-14)
// ============================================================
async function loadNotifications() {
    try {
        const r = await api('/api/v1/notifications/');
        if (!r) return;
        const data = await r.json();
        const notifs = Array.isArray(data) ? data : (data.results || []);
        window._notifCache = notifs;

        const unreadCount = notifs.filter(n => !n.read).length;
        const dot = document.getElementById('notif-dot');
        if (dot) dot.classList.toggle('show', unreadCount > 0);

        renderNotifPanel(notifs);
    } catch(e) {}
}

function renderNotifPanel(notifs) {
    const panel = document.getElementById('notif-panel');
    if (!panel) return;
    if (!notifs.length) {
        panel.innerHTML = '<div class="notif-empty">Nenhuma notificação por enquanto.</div>';
        return;
    }
    panel.innerHTML = notifs.slice(0, 20).map(n => `
        <div class="notif-item ${n.read ? '' : 'unread'}" onclick="markNotifRead(${n.id})">
            <div class="notif-item-title">${n.titulo}</div>
            <div class="notif-item-msg">${n.mensagem}</div>
        </div>
    `).join('');
}

function toggleNotifPanel() {
    const panel = document.getElementById('notif-panel');
    if (panel) panel.classList.toggle('show');
}

async function markNotifRead(id) {
    try {
        await api(`/api/v1/notifications/${id}/read/`, { method: 'POST' });
        loadNotifications();
    } catch(e) {}
}

// ============================================================
// MAPA DE OCORRÊNCIAS — RF26
// Cole este bloco no FINAL do seu admin.js
// Dependência: Leaflet.js (adicionada automaticamente no loadMapPage)
// ============================================================

// Tiles do OpenStreetMap (os tiles da CARTO passaram a exigir chave de API)
const OSM_TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const OSM_ATTRIBUTION = '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

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

    // OpenStreetMap (sem chave de API) com filtro escuro via CSS
    L.tileLayer(OSM_TILES, {
        attribution: OSM_ATTRIBUTION,
        maxZoom: 19,
        className: 'dark-tiles',   // escurece os tiles via CSS (tema dark do admin)
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
            <span>${cat ? esc(cat.name) : '—'}</span>
        </div>
        <div><span style="color:var(--text3)">Status:</span> ${STATUS_LABEL[occ.status] || occ.status}</div>
        ${occ.address ? `<div><span style="color:var(--text3)">Endereço:</span> ${esc(occ.address)}</div>` : ''}
        ${occ.importance_color ? `<div><span style="color:var(--text3)">Importância:</span> ${IMPORTANCE_LABEL[occ.importance_color] || occ.importance_color}</div>` : ''}
        <div><span style="color:var(--text3)">Validações:</span> ${occ.validation_count || 0}</div>
        <div><span style="color:var(--text3)">Prazo:</span> ${slaBadge(occ)}</div>
        <div><span style="color:var(--text3)">Data:</span> ${fmt(occ.created_at)}</div>
        <button class="btn btn-primary btn-sm" style="margin-top:6px;justify-content:center"
                onclick="document.getElementById('map-popup').style.display='none';openOccDetail(${occ.id})">Ver detalhes</button>
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