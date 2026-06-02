// ============================================================
// CONFIGURAÇÃO DA API — padrão Aula 05/08 (Prof. Negretto)
// ============================================================
const API_BASE = 'http://127.0.0.1:9000';

function getToken() {
    return localStorage.getItem('infraMind_access_token');
}

function getSession() {
    return {
        name:  localStorage.getItem('infraMind_session_name'),
        email: localStorage.getItem('infraMind_session_email'),
        id:    localStorage.getItem('infraMind_session_id'),
    };
}

async function apiFetch(path, options = {}) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (options.body instanceof FormData) delete headers['Content-Type'];

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

    if (res.status === 401) {
        const refreshed = await tryRefreshToken();
        if (refreshed) {
            headers['Authorization'] = `Bearer ${getToken()}`;
            return fetch(`${API_BASE}${path}`, { ...options, headers });
        } else {
            logout();
            return res;
        }
    }
    return res;
}

async function tryRefreshToken() {
    const refresh = localStorage.getItem('infraMind_refresh_token');
    if (!refresh) return false;
    try {
        const res = await fetch(`${API_BASE}/authentication/token/refresh/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh }),
        });
        if (!res.ok) return false;
        const data = await res.json();
        localStorage.setItem('infraMind_access_token', data.access);
        return true;
    } catch { return false; }
}

// ============================================================
// NAVEGAÇÃO
// ============================================================
const screens     = document.querySelectorAll('.screen');
const header      = document.getElementById('top-header');
const sidebar     = document.getElementById('app-sidebar');
const mainContent = document.getElementById('main-content');

const ICON_EYE_OPEN   = `<svg viewBox="0 0 24 24" class="eye-icon"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>`;
const ICON_EYE_CLOSED = `<svg viewBox="0 0 24 24" class="eye-icon"><path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.82l2.92 2.92c1.51-1.26 2.7-2.89 3.44-4.74-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z"/></svg>`;

function navigateTo(screenId, id = null) {
    screens.forEach(s => s.classList.add('hidden'));
    document.getElementById(screenId).classList.remove('hidden');
    const session = getSession();

    if (['login-screen', 'register-screen'].includes(screenId)) {
        header.classList.add('hidden');
        sidebar.classList.add('hidden');
        mainContent.style.marginLeft = '0';
    } else {
        if (!session.email) { navigateTo('login-screen'); return; }
        header.classList.remove('hidden');
        sidebar.classList.remove('hidden');
        mainContent.style.marginLeft = '260px';
        document.getElementById('display-user-name').innerText = session.name;
    }

    if (screenId === 'list-screen')    renderList();
    if (screenId === 'details-screen') renderDetails(id);
    if (screenId === 'edit-screen')    loadEditData(id);
    if (screenId === 'admin-screen')   renderAdmin();
    if (screenId === 'create-screen')  loadCategories('category');
    window.scrollTo(0, 0);
}

function togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
        btn.innerHTML = ICON_EYE_CLOSED;
    } else {
        input.type = 'password';
        btn.innerHTML = ICON_EYE_OPEN;
    }
}

// ============================================================
// AUTENTICAÇÃO — padrão Aula 08 (JWT)
// ============================================================

// CADASTRO → POST /api/users/register/ (AllowAny)
document.getElementById('register-form').onsubmit = async (e) => {
    e.preventDefault();
    const fullName = document.getElementById('reg-name').value;
    const username = fullName.trim().replace(/\s+/g, '_').toLowerCase();
    const payload  = {
        username,
        first_name: fullName.split(' ')[0],
        last_name:  fullName.split(' ').slice(1).join(' '),
        email:      document.getElementById('reg-email').value,
        password:   document.getElementById('reg-password').value,
    };
    try {
        const res = await fetch(`${API_BASE}/api/v1/users/register/`, { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) { alert('Erro no cadastro: ' + JSON.stringify(data)); return; }
        await doLogin(payload.username, payload.password);
    } catch (err) {
        alert('Erro de conexão com a API.');
        console.error(err);
    }
};

// LOGIN → POST /authentication/token/ (padrão Aula 08)
document.getElementById('login-form').onsubmit = async (e) => {
    e.preventDefault();
    await doLogin(
        document.getElementById('login-email').value,
        document.getElementById('login-password').value
    );
};

async function doLogin(username, password) {
    try {
        const res  = await fetch(`${API_BASE}/authentication/token/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        const data = await res.json();
        if (!res.ok) { alert('Falha na autenticação. Verifique suas credenciais.'); return; }

        localStorage.setItem('infraMind_access_token',  data.access);
        localStorage.setItem('infraMind_refresh_token', data.refresh);
        await loadCurrentUser();
        navigateTo('list-screen');
    } catch (err) {
        alert('Erro de conexão com a API.');
        console.error(err);
    }
}

async function loadCurrentUser() {
    try {
        const payload = JSON.parse(atob(getToken().split('.')[1]));
        const userId  = payload.user_id;
        const res     = await apiFetch('/api/v1/users/');
        const data    = await res.json();
        const users   = Array.isArray(data) ? data : (data.results || []);
        const me      = users.find(u => u.id === userId);
        if (me) {
            const name = (me.first_name && me.last_name)
                ? `${me.first_name} ${me.last_name}`
                : me.username;
            localStorage.setItem('infraMind_session_name',  name);
            localStorage.setItem('infraMind_session_email', me.email);
            localStorage.setItem('infraMind_session_id',    me.id);
        }
    } catch (err) { console.error('Erro ao carregar usuário:', err); }
}

function logout() {
    ['infraMind_access_token','infraMind_refresh_token',
     'infraMind_session_name','infraMind_session_email','infraMind_session_id']
        .forEach(k => localStorage.removeItem(k));
    location.reload();
}

// ============================================================
// CATEGORIAS — GET /api/categories/
// ============================================================
async function loadCategories(selectId) {
    try {
        const res  = await apiFetch('/api/v1/categories/');
        const data = await res.json();
        const cats = Array.isArray(data) ? data : (data.results || []);
        const sel  = document.getElementById(selectId);
        sel.innerHTML = '<option value="" disabled selected>Selecione a categoria</option>';
        cats.forEach(cat => {
            const opt = document.createElement('option');
            opt.value       = cat.id;
            opt.textContent = cat.name;
            sel.appendChild(opt);
        });
    } catch (err) { console.error('Erro ao carregar categorias:', err); }
}

// ============================================================
// CRIAR OCORRÊNCIA — POST /api/occurrences/ + POST /api/images/
// ============================================================
document.getElementById('create-form').onsubmit = async (e) => {
    e.preventDefault();
    const payload = {
        title:       document.getElementById('problem-title').value,
        category:    document.getElementById('category').value || null,
        address:     document.getElementById('location').value,
        description: document.getElementById('description').value,
        status:      'open',
    };
    try {
        const res  = await apiFetch('/api/v1/occurrences/', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
        const data = await res.json();

        // ── Duplicata detectada ──────────────────────────────────────────
        if (data?.duplicate === true) {
            const existing = data.original_occurrence || {};
            const info = existing.address ? ` no endereço "${existing.address}"` : '';
            const confirmView = existing.id && confirm(
                `   Esta ocorrência já foi registrada${info}.\n` +
                `Sua confirmação foi somada ao registro existente.\n\n` +
                `Deseja visualizar a ocorrência original?`
            );
            if (confirmView) navigateTo('details-screen', existing.id);
            return; // interrompe — não tenta acessar occ.id
        }
        // ────────────────────────────────────────────────────────────────

        if (!res.ok) {
            alert('Erro ao criar ocorrência: ' + JSON.stringify(data));
            return;
        }

        // Sucesso: sobe imagem e redireciona
        const occId = data.occurrence?.id ?? data.id;
        const file  = document.getElementById('image-upload').files[0];
        if (file && occId) await uploadImage(occId, file);

        e.target.reset();
        navigateTo('list-screen');
    } catch (err) {
        alert('Erro de conexão com a API.');
        console.error(err);
    }
};

async function uploadImage(occurrenceId, file) {
    const formData = new FormData();
    formData.append('occurrence', occurrenceId);
    formData.append('image_file', file);
    try {
        await apiFetch('/api/v1/images/', { method: 'POST', body: formData, headers: {} });
    } catch (err) { console.error('Erro ao enviar imagem:', err); }
}

// ============================================================
// LISTAR OCORRÊNCIAS — GET /api/occurrences/
// ============================================================
async function renderList() {
    const container = document.getElementById('occurrence-list');
    container.innerHTML = '<p style="color:#64748b;padding:32px;text-align:center;">Carregando...</p>';
    try {
        const res   = await apiFetch('/api/v1/occurrences/');
        const data  = await res.json();
        const all   = Array.isArray(data) ? data : (data.results || []);
        const session = getSession();
        const items = all.filter(o => String(o.user) === String(session.id));

        container.innerHTML = '';
        if (items.length === 0) {
            container.innerHTML = `<div class="content-card" style="grid-column:1/-1;text-align:center;color:#64748b;padding:48px;">Nenhum registro encontrado no seu perfil.</div>`;
            return;
        }

        [...items].reverse().forEach(occ => {
            const imgSrc = (occ.images && occ.images.length > 0)
                ? (occ.images[0].image_file || occ.images[0].url)
                : 'https://via.placeholder.com/400x200?text=S/IMAGEM';
            const div = document.createElement('div');
            div.className = 'occurrence-card';
            div.innerHTML = `
                <img src="${imgSrc}" class="occ-img" onerror="this.src='https://via.placeholder.com/400x200?text=S/IMAGEM'">
                <div class="occ-body">
                    <h3>${occ.title}</h3>
                    <p>${occ.address || ''}</p>
                    <div class="card-actions">
                        <button class="btn secondary-btn" style="padding:8px 16px" onclick="navigateTo('details-screen', ${occ.id})">Acessar</button>
                        <div style="display:flex;gap:8px;">
                            <button class="edit-btn-small" onclick="navigateTo('edit-screen', ${occ.id})">Editar</button>
                            <button class="danger-btn-small" onclick="deleteOcc(${occ.id})">Remover</button>
                        </div>
                    </div>
                </div>`;
            container.appendChild(div);
        });
    } catch (err) {
        container.innerHTML = '<p style="color:red;padding:32px;">Erro ao carregar ocorrências.</p>';
        console.error(err);
    }
}

// ============================================================
// DETALHES — GET /api/occurrences/<id>/
// ============================================================
async function renderDetails(id) {
    try {
        const res = await apiFetch(`/api/v1/occurrences/${id}/`);
        const occ = await res.json();

        document.getElementById('detail-title').innerText       = occ.title;
        document.getElementById('detail-status').innerText      = occ.status;
        document.getElementById('detail-date').innerText        = new Date(occ.created_at).toLocaleDateString('pt-BR');
        document.getElementById('detail-location').innerText    = occ.address || '—';
        document.getElementById('detail-description').innerText = occ.description;
        document.getElementById('detail-reporter-name').innerText = 'Analista: ' + getSession().name;

        const imgEl  = document.getElementById('detail-image');
        const imgSrc = (occ.images && occ.images.length > 0)
            ? (occ.images[0].image_file || occ.images[0].url) : null;
        if (imgSrc) { imgEl.src = imgSrc; imgEl.style.display = 'block'; }
        else imgEl.style.display = 'none';

        document.querySelector('.detail-actions').innerHTML = `
            <button class="btn secondary-btn" onclick="navigateTo('list-screen')">Retornar à Lista</button>
            <button class="btn primary-btn" onclick="navigateTo('edit-screen', ${occ.id})">Editar Registro</button>
            <button class="btn" style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;" onclick="deleteOcc(${occ.id})">Excluir Permanentemente</button>`;
    } catch (err) { console.error('Erro ao carregar detalhes:', err); }
}

// ============================================================
// EDITAR — GET + PATCH /api/occurrences/<id>/
// ============================================================
async function loadEditData(id) {
    await loadCategories('edit-category');
    try {
        const res = await apiFetch(`/api/v1/occurrences/${id}/`);
        const occ = await res.json();

        document.getElementById('edit-id').value            = occ.id;
        document.getElementById('edit-problem-title').value = occ.title;
        document.getElementById('edit-location').value      = occ.address || '';
        document.getElementById('edit-description').value   = occ.description;
        if (occ.category) document.getElementById('edit-category').value = occ.category;

        const imgEl  = document.getElementById('edit-current-image');
        const imgSrc = (occ.images && occ.images.length > 0)
            ? (occ.images[0].image_file || occ.images[0].url) : null;
        if (imgSrc) { imgEl.src = imgSrc; imgEl.style.display = 'block'; }
        else imgEl.style.display = 'none';
    } catch (err) { console.error('Erro ao carregar dados para edição:', err); }
}

document.getElementById('edit-form').onsubmit = async (e) => {
    e.preventDefault();
    const id = document.getElementById('edit-id').value;
    const payload = {
        title:       document.getElementById('edit-problem-title').value,
        category:    document.getElementById('edit-category').value || null,
        address:     document.getElementById('edit-location').value,
        description: document.getElementById('edit-description').value,
    };
    try {
        const res = await apiFetch(`/api/v1/occurrences/${id}/`, {
            method: 'PATCH',
            body: JSON.stringify(payload),
        });
        if (!res.ok) { const err = await res.json(); alert('Erro: ' + JSON.stringify(err)); return; }

        const file = document.getElementById('edit-image-upload').files[0];
        if (file) await uploadImage(id, file);

        navigateTo('details-screen', Number(id));
    } catch (err) {
        alert('Erro de conexão com a API.');
        console.error(err);
    }
};

// ============================================================
// EXCLUIR — DELETE /api/occurrences/<id>/
// ============================================================
async function deleteOcc(id) {
    if (!confirm('Confirmar a exclusão permanente deste registro técnico?')) return;
    try {
        await apiFetch(`/api/v1/occurrences/${id}/`, { method: 'DELETE' });
        navigateTo('list-screen');
    } catch (err) { alert('Erro ao excluir.'); console.error(err); }
}

// ============================================================
// PAINEL ADMIN — GET /api/occurrences/
// ============================================================
async function renderAdmin() {
    try {
        const res   = await apiFetch('/api/v1/occurrences/');
        const data  = await res.json();
        const all   = Array.isArray(data) ? data : (data.results || []);
        const mine  = all.filter(o => String(o.user) === String(getSession().id));
        document.getElementById('stat-total').innerText      = all.length;
        document.getElementById('stat-user-total').innerText = mine.length;
    } catch (err) { console.error('Erro ao carregar painel:', err); }
}

// ============================================================
// INICIALIZAÇÃO
// ============================================================
if (getToken() && getSession().email) {
    navigateTo('list-screen');
} else {
    navigateTo('login-screen');
}
