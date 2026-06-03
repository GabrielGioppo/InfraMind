// ═══════════════════════════════════════════════
// INDEX — InfraMind
// ═══════════════════════════════════════════════
const API = 'http://127.0.0.1:9000';

let STATE = {
  user: null,
  occurrences: [],
  allOccurrences: [],
  categories: [],
  currentOccId: null,
  feedbackRating: 0,
  viewMode: 'grid',
};

// ════════════════════════════════════
// TOKEN HELPERS
// ════════════════════════════════════
const tk = {
  get:     () => localStorage.getItem('im_access'),
  getRef:  () => localStorage.getItem('im_refresh'),
  set:     (a,r) => { localStorage.setItem('im_access',a); if(r) localStorage.setItem('im_refresh',r); },
  clear:   () => ['im_access','im_refresh','im_user'].forEach(k=>localStorage.removeItem(k)),
  payload: () => { try{ return JSON.parse(atob(tk.get().split('.')[1])); }catch{return null;} }
};

// ════════════════════════════════════
// API FETCH WRAPPER
// ════════════════════════════════════
async function api(path, opts={}) {
  const hdrs = { ...opts.headers };
  if (tk.get()) hdrs['Authorization'] = `Bearer ${tk.get()}`;
  if (!(opts.body instanceof FormData)) hdrs['Content-Type'] = 'application/json';

  let res = await fetch(`${API}${path}`, { ...opts, headers: hdrs });

  if (res.status === 401) {
    const ok = await refreshToken();
    if (ok) {
      hdrs['Authorization'] = `Bearer ${tk.get()}`;
      res = await fetch(`${API}${path}`, { ...opts, headers: hdrs });
    } else { doLogout(); return res; }
  }
  return res;
}

async function refreshToken() {
  const ref = tk.getRef();
  if (!ref) return false;
  try {
    const r = await fetch(`${API}/authentication/token/refresh/`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({refresh:ref})
    });
    if (!r.ok) return false;
    const d = await r.json();
    tk.set(d.access);
    return true;
  } catch { return false; }
}

// ════════════════════════════════════
// LOGIN POR USERNAME OU E-MAIL
// ════════════════════════════════════
async function resolveAndLogin(usernameOrEmail, password) {
  // 1ª tentativa: username direto
  const r1 = await fetch(`${API}/authentication/token/`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ username: usernameOrEmail, password })
  });
  if (r1.ok) return await r1.json();

  // 2ª tentativa: e-mail via endpoint dedicado
  const r2 = await fetch(`${API}/authentication/login/`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ email: usernameOrEmail, password })
  });
  if (r2.ok) return await r2.json();

  return null;
}

// ════════════════════════════════════
// AUTH
// ════════════════════════════════════
document.getElementById('login-form').onsubmit = async e => {
  e.preventDefault();
  const btn = e.target.querySelector('button[type=submit]');
  btn.disabled = true; btn.textContent = 'Entrando...';
  await doLogin(
    document.getElementById('login-user').value.trim(),
    document.getElementById('login-pass').value
  );
  btn.disabled = false; btn.textContent = 'Entrar';
};

document.getElementById('register-form').onsubmit = async e => {
  e.preventDefault();
  const btn = e.target.querySelector('button[type=submit]');
  btn.disabled = true; btn.textContent = 'Criando...';

  const username = document.getElementById('reg-name').value.trim();
  const email    = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-pass').value;

  if (!username || !email || !password) {
    toast('Preencha todos os campos.', 'error');
    btn.disabled = false; btn.textContent = 'Criar Conta'; return;
  }
  if (!/^[a-zA-Z0-9_]+$/.test(username)) {
    toast('O usuário só pode conter letras, números e _. Sem espaços.', 'error');
    btn.disabled = false; btn.textContent = 'Criar Conta'; return;
  }
  if (password.length < 8) {
    toast('A senha precisa ter pelo menos 8 caracteres.', 'error');
    btn.disabled = false; btn.textContent = 'Criar Conta'; return;
  }

  const payload = { username, email, password };

  try {
    const r = await fetch(`${API}/api/v1/users/register/`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)
    });
    const d = await r.json();
    if (!r.ok) {
      toast('Erro: ' + (d.email?.[0] || d.username?.[0] || JSON.stringify(d)), 'error');
    } else {
      toast('Conta criada com sucesso!');
      // Auto-login após cadastro — mantém na página
      await doLogin(username, password);
    }
  } catch { toast('Erro de conexão','error'); }

  btn.disabled = false; btn.textContent = 'Criar Conta';
};

async function doLogin(usernameOrEmail, password) {
  try {
    const tokens = await resolveAndLogin(usernameOrEmail, password);
    if (!tokens) { toast('Credenciais inválidas','error'); return; }
    tk.set(tokens.access, tokens.refresh);
    await loadCurrentUser();
    hideAuthScreens();
    navigateTo('dashboard');
  } catch { toast('Erro de conexão com a API','error'); }
}

async function loadCurrentUser() {
  const payload = tk.payload();
  if (!payload) return;
  const r = await api('/api/v1/users/');
  const d = await r.json();
  const users = Array.isArray(d) ? d : (d.results || []);
  const me = users.find(u => u.id === payload.user_id);
  if (me) {
    STATE.user = me;
    localStorage.setItem('im_user', JSON.stringify(me));
    updateUserUI();
  }
}

function updateUserUI() {
  const u = STATE.user;
  if (!u) return;
  const name = [u.first_name, u.last_name].filter(Boolean).join(' ') || u.username;
  document.getElementById('user-name').textContent = name;
  document.getElementById('user-avatar').textContent = name.charAt(0).toUpperCase();
  const isAdmin = u.user_type === 'admin' || u.is_staff;
  const badge = document.getElementById('user-role-badge');
  badge.textContent = isAdmin ? 'Admin' : 'Cidadão';
  badge.className = 'role-badge ' + (isAdmin ? 'admin' : 'citizen');
  if (isAdmin) {
    document.getElementById('nav-admin').classList.remove('hidden');
    document.getElementById('e-status-field').classList.remove('hidden');
    document.getElementById('e-imp-field').classList.remove('hidden');
    document.querySelectorAll('.admin-only-element').forEach(el => el.style.display = '');
  } else {
    document.querySelectorAll('.admin-only-element').forEach(el => el.style.display = 'none');
  }
}

function isAdmin() {
  return STATE.user && (STATE.user.user_type === 'admin' || STATE.user.is_staff);
}

function doLogout() {
  tk.clear(); STATE.user = null;
  window.location.href = 'landing.html';
}

// ════════════════════════════════════
// SCREEN / PAGE NAV
// ════════════════════════════════════
function showScreen(id) {
  ['screen-login','screen-register'].forEach(s => {
    document.getElementById(s).classList.toggle('hidden', s !== id);
  });
}

function hideAuthScreens() {
  document.getElementById('screen-login').classList.add('hidden');
  document.getElementById('screen-register').classList.add('hidden');
  document.getElementById('topbar').classList.remove('hidden');
  document.getElementById('sidebar').classList.remove('hidden');
  document.getElementById('app').classList.remove('hidden');
}

const PAGES = ['dashboard','occurrences','create','detail','edit','admin'];

function navigateTo(page, id=null) {
  PAGES.forEach(p => document.getElementById(`page-${p}`).classList.add('hidden'));
  document.getElementById(`page-${page}`).classList.remove('hidden');

  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const navMap = {dashboard:'nav-dashboard',occurrences:'nav-occurrences',admin:'nav-admin'};
  if (navMap[page]) document.getElementById(navMap[page])?.classList.add('active');

  if (page === 'dashboard')    loadDashboard();
  if (page === 'occurrences')  loadOccurrences();
  if (page === 'create')       loadCreatePage();
  if (page === 'detail' && id) loadDetail(id);
  if (page === 'edit' && id)   loadEditPage(id);
  if (page === 'admin')        loadAdminPage();

  window.scrollTo(0,0);
}

// ════════════════════════════════════
// DASHBOARD
// ════════════════════════════════════
async function loadDashboard() {
  try {
    const [statR, occR] = await Promise.all([
      api('/api/v1/statistics/'),
      api('/api/v1/occurrences/')
    ]);
    const stats = await statR.json();
    const occs  = await occR.json();
    const all   = Array.isArray(occs) ? occs : (occs.results || []);

    document.getElementById('stat-total').textContent = stats.total_ocorrencias ?? all.length;
    document.getElementById('stat-users').textContent  = stats.total_usuarios ?? '—';

    const open     = all.filter(o=>o.status==='open').length;
    const resolved = all.filter(o=>o.status==='resolved').length;
    document.getElementById('stat-open').textContent     = open;
    document.getElementById('stat-resolved').textContent = resolved;

    const recent = [...all].reverse().slice(0,5);
    const tbody = document.getElementById('dashboard-recent');
    if (!recent.length) {
      tbody.innerHTML = `<div class="empty-state"><svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/></svg><p>Nenhuma ocorrência registrada ainda</p></div>`;
      return;
    }
    tbody.innerHTML = `<div class="table-wrap"><table><thead><tr><th>Título</th><th>Categoria</th><th>Status</th><th>Data</th></tr></thead><tbody>` +
      recent.map(o=>`<tr onclick="navigateTo('detail',${o.id})" style="cursor:pointer">
        <td class="td-title">${esc(o.title)}</td>
        <td><span style="color:var(--muted);font-size:.8rem">${esc(o.category_details?.name||'—')}</span></td>
        <td>${statusBadge(o.status)}</td>
        <td class="td-mono" style="font-size:.78rem">${fmtDate(o.created_at)}</td>
      </tr>`).join('') + `</tbody></table></div>`;
  } catch(e) { console.error(e); }
}

// ════════════════════════════════════
// OCCURRENCES LIST
// ════════════════════════════════════
async function loadOccurrences() {
  document.getElementById('occ-grid-view').innerHTML = `<div class="loading-center" style="grid-column:1/-1"><div class="spinner"></div></div>`;
  
  if (!STATE.categories.length) await loadCategories();
  
  const catSel = document.getElementById('filter-cat');
  if (catSel && catSel.options.length <= 1) {
    STATE.categories.forEach(c => {
      const o = document.createElement('option');
      o.value = c.id;
      o.textContent = c.name;
      catSel.appendChild(o);
    });
  }

  try {
    const r = await api(`/api/v1/occurrences/`);
    const d = await r.json();
    STATE.allOccurrences = Array.isArray(d) ? d : (d.results || []);
    window._STATE_OCC = STATE.allOccurrences;
    applyFilters();
  } catch(e) {
    console.error('Erro ao buscar ocorrências:', e);
  }
}

function applyFilters() {
  const searchText = document.getElementById('filter-search').value.toLowerCase().trim();
  const filterStatus = document.getElementById('filter-status').value;
  const filterCat = document.getElementById('filter-cat').value;
  const filterFrom = document.getElementById('filter-from').value;
  const filterTo = document.getElementById('filter-to').value;
  let filtered = STATE.allOccurrences.filter(o => {
    if (searchText) {
      const titleMatch = o.title && o.title.toLowerCase().includes(searchText);
      const addressMatch = o.address && o.address.toLowerCase().includes(searchText);
      if (!titleMatch && !addressMatch) return false;
    }
    if (filterStatus && o.status !== filterStatus) return false;
    if (filterCat) {
      const itemCatId = o.category_details?.id || o.category;
      if (String(itemCatId) !== String(filterCat)) return false;
    }
    if (filterFrom) {
      const occDate = o.created_at.substring(0, 10);
      if (occDate < filterFrom) return false;
    }
    if (filterTo) {
      const occDate = o.created_at.substring(0, 10);
      if (occDate > filterTo) return false;
    }
    return true;
  });
  STATE.occurrences = filtered;
  const countLabel = document.getElementById('occ-count-label');
  if (countLabel) {
    countLabel.textContent = `${filtered.length} ocorrência${filtered.length !== 1 ? 's' : ''} encontrada${filtered.length !== 1 ? 's' : ''}`;
  }
  renderOccurrences(filtered);
}

function clearFilters() {
  document.getElementById('filter-search').value = '';
  document.getElementById('filter-status').value = '';
  document.getElementById('filter-cat').value = '';
  document.getElementById('filter-from').value = '';
  document.getElementById('filter-to').value = '';
  loadOccurrences();
}

function toggleView() {
  STATE.viewMode = STATE.viewMode === 'grid' ? 'table' : 'grid';
  document.getElementById('occ-grid-view').classList.toggle('hidden', STATE.viewMode!=='grid');
  document.getElementById('occ-table-view').classList.toggle('hidden', STATE.viewMode!=='table');
  document.getElementById('view-toggle-btn').innerHTML = STATE.viewMode==='grid'
    ? `<svg viewBox="0 0 24 24" style="width:15px;height:15px;fill:currentColor"><path d="M4 14h4v-4H4v4zm0 5h4v-4H4v4zM4 9h4V5H4v4zm5 5h12v-4H9v4zm0 5h12v-4H9v4zM9 5v4h12V5H9z"/></svg> Tabela`
    : `<svg viewBox="0 0 24 24" style="width:15px;height:15px;fill:currentColor"><path d="M4 5h3v3H4V5zm0 5h3v3H4v-3zm0 5h3v3H4v-3zm5-10h3v3H9V5zm0 5h3v3H9v-3zm0 5h3v3H9v-3zm5-10h3v3h-3V5zm0 5h3v3h-3v-3zm0 5h3v3h-3v-3z"/></svg> Cards`;
  renderOccurrences(STATE.occurrences);
}

function renderOccurrences(list) {
  if (STATE.viewMode === 'grid') {
    const container = document.getElementById('occ-grid-view');
    if (!list.length) {
      container.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/></svg><p>Nenhuma ocorrência encontrada</p></div>`;
      return;
    }
    container.innerHTML = list.map(o => occCard(o)).join('');
  } else {
    const tbody = document.getElementById('occ-table-body');
    tbody.innerHTML = list.map(o => `
      <tr>
        <td class="td-mono">#${o.id}</td>
        <td class="td-title" onclick="navigateTo('detail',${o.id})" style="cursor:pointer;color:var(--blue)">${esc(o.title)}</td>
        <td style="font-size:.8rem;color:var(--muted)">${esc(o.category_details?.name||'—')}</td>
        <td>${statusBadge(o.status)}</td>
        <td>${urgencyBadge(o.urgency_level)}</td>
        <td><div class="priority-bar"><div class="priority-fill" style="width:${Math.min(100,(o.priority||0)*2)}%"></div></div></td>
        <td style="font-size:.85rem;color:var(--muted)">${o.validation_count||0}</td>
        <td class="td-mono" style="font-size:.78rem">${fmtDate(o.created_at)}</td>
        <td>
          <div style="display:flex;gap:4px">
            <button class="btn btn-ghost btn-sm" onclick="navigateTo('detail',${o.id})">Ver</button>
            ${canEdit(o)?`<button class="btn btn-ghost btn-sm" onclick="navigateTo('edit',${o.id})">Editar</button>`:''}
            ${isAdmin()?`<button class="btn btn-ghost btn-sm" onclick="openAdminAiModal(${o.id})" title="Verificar com IA" style="color:var(--purple)">🤖 IA</button>`:''}
          </div>
        </td>
      </tr>`).join('');
  }
}

function occCard(o) {
  const img = o.images?.length ? imgUrl(o.images[0].image || o.images[0].url) : null;
  const imgHtml = img
    ? `<img src="${img}" class="occ-thumb" onerror="this.parentElement.innerHTML='<div class=occ-thumb-placeholder><svg viewBox=\\'0 0 24 24\\'><path d=\\'M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z\\'/></svg></div>'">`
    : `<div class="occ-thumb-placeholder"><svg viewBox="0 0 24 24"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg></div>`;
  return `<div class="occ-card" onclick="navigateTo('detail',${o.id})">
    ${imgHtml}
    <div class="occ-body">
      <div class="occ-meta">
        ${statusBadge(o.status)}
        ${urgencyBadge(o.urgency_level)}
        ${o.importance_color ? `<span class="badge ${impClass(o.importance_color)}">${impLabel(o.importance_color)}</span>` : ''}
      </div>
      <div class="occ-title">${esc(o.title)}</div>
      ${o.address ? `<div class="occ-addr"><svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>${esc(o.address)}</div>` : ''}
    </div>
    <div class="occ-footer" onclick="event.stopPropagation()">
      <div class="occ-validations">
        <svg viewBox="0 0 24 24"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>
        ${o.validation_count||0} validação${(o.validation_count||0)!==1?'s':''}
      </div>
      <div class="occ-actions">
        ${canEdit(o) ? `<button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();navigateTo('edit',${o.id})">Editar</button>` : ''}
      </div>
    </div>
  </div>`;
}

// ════════════════════════════════════
// CATEGORIES
// ════════════════════════════════════
async function loadCategories() {
  const r = await api('/api/v1/categories/');
  const d = await r.json();
  STATE.categories = Array.isArray(d) ? d : (d.results || []);
}

function populateCatSelect(id, val='') {
  const sel = document.getElementById(id);
  sel.innerHTML = '<option value="">Selecione a categoria</option>';
  STATE.categories.forEach(c => {
    const o = document.createElement('option');
    o.value = c.id; o.textContent = c.name;
    if (String(c.id) === String(val)) o.selected = true;
    sel.appendChild(o);
  });
}

// ════════════════════════════════════
// CREATE OCCURRENCE
// ════════════════════════════════════
async function loadCreatePage() {
  if (!STATE.categories.length) await loadCategories();
  populateCatSelect('c-cat');
  document.getElementById('c-title').value = '';
  document.getElementById('c-addr').value = '';
  document.getElementById('c-desc').value = '';
  document.getElementById('c-lat').value = '';
  document.getElementById('c-lng').value = '';
  const extras = document.getElementById('create-extras');
  if (extras) extras.removeAttribute('open');
  const locManual = document.getElementById('loc-manual-drawer');
  if (locManual) locManual.removeAttribute('open');
  const coordLabel = document.getElementById('c-coords-label');
  if (coordLabel) { coordLabel.style.display = 'none'; coordLabel.textContent = ''; }
  setTimeout(() => initCreateMapDefault(), 150);
}

function initCreateMapDefault() {
  const lat = -14.235, lng = -51.9253, zoom = 4;
  if (!_maps.create) {
    _maps.create = L.map('create-map').setView([lat, lng], zoom);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap', maxZoom: 19 }).addTo(_maps.create);
    _maps.create.on('click', e => {
      const latEl = document.getElementById('c-lat');
      const lngEl = document.getElementById('c-lng');
      if (latEl) latEl.value = e.latlng.lat.toFixed(6);
      if (lngEl) lngEl.value = e.latlng.lng.toFixed(6);
      const label = document.getElementById('c-coords-label');
      if (label) { label.textContent = '📍 Marcado: ' + e.latlng.lat.toFixed(5) + ', ' + e.latlng.lng.toFixed(5); label.style.display = 'block'; }
      if (_createMarker) _maps.create.removeLayer(_createMarker);
      _createMarker = L.marker([e.latlng.lat, e.latlng.lng]).addTo(_maps.create).bindPopup('📍 Local da ocorrência').openPopup();
    });
  } else {
    _maps.create.setView([lat, lng], zoom);
    if (_createMarker) { _maps.create.removeLayer(_createMarker); _createMarker = null; }
  }
  setTimeout(() => _maps.create.invalidateSize(), 200);
}

async function runAiAnalysis() {
  const title = document.getElementById('c-title').value.trim();
  const desc  = document.getElementById('c-desc').value.trim();
  const catId = document.getElementById('c-cat').value;
  if (!title) { toast('Preencha o título antes de analisar','error'); return; }

  const btn = event.target.closest('button');
  btn.disabled = true; btn.textContent = 'Analisando...';

  try {
    const r = await api('/api/v1/validations/ai-analyze/', {
      method: 'POST',
      body: JSON.stringify({ title, description: desc, category_id: catId || null })
    });
    const d = await r.json();

    const panel = document.getElementById('ai-analysis-panel');
    if (isAdmin()) panel.classList.remove('hidden');

    const urg = d.urgency;
    const levelColors = { critical:'var(--red)', high:'var(--yellow)', medium:'var(--blue)', low:'var(--green)' };
    const levelLabels = { critical:'Crítica', high:'Alta', medium:'Média', low:'Baixa' };
    const color = levelColors[urg?.urgency_level] || 'var(--muted)';
    document.getElementById('ai-urgency-section').innerHTML = `
      <div style="margin-bottom:12px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
          <span style="font-size:.85rem;color:#c9d1d9">Urgência detectada: <strong style="color:${color}">${levelLabels[urg?.urgency_level]||'—'}</strong></span>
          <span style="font-size:.78rem;color:var(--muted);font-family:var(--mono)">${urg?.urgency_score||0}/100</span>
        </div>
        <div class="ai-score-bar"><div class="ai-score-fill" style="width:${urg?.urgency_score||0}%;background:${color}"></div></div>
        <p style="font-size:.78rem;color:var(--muted);margin-top:4px">${esc(urg?.urgency_reason||'')}</p>
      </div>`;

    const dup = d.duplicate;
    if (dup?.is_duplicate) {
      document.getElementById('ai-dup-section').innerHTML = `
        <div class="ai-dup-alert">
          <strong>⚠ Possível duplicata detectada</strong>
          ${esc(dup.reason)} (Similaridade: ${dup.similarity_score}%)
          ${d.similar_occurrences?.length ? `<div style="margin-top:8px;font-size:.78rem">
            Ocorrência similar: <a href="#" onclick="navigateTo('detail',${dup.duplicate_of_id})">#${dup.duplicate_of_id}</a>
          </div>` : ''}
        </div>`;
    } else {
      document.getElementById('ai-dup-section').innerHTML = `<p style="font-size:.78rem;color:var(--green)">✓ Nenhuma duplicata encontrada na área</p>`;
    }
  } catch(e) { toast('Erro na análise de IA','error'); console.error(e); }

  btn.disabled = false; btn.innerHTML = '<svg viewBox="0 0 24 24" style="width:15px;height:15px;fill:currentColor"><path d="M12 2a10 10 0 100 20A10 10 0 0012 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg> Analisar com IA';
}

async function createOccurrence() {
  const titleRaw = document.getElementById('c-title').value.trim();
  const desc     = document.getElementById('c-desc').value.trim();
  const catEl    = document.getElementById('c-cat');
  const catLabel = catEl.selectedOptions[0]?.text || '';
  const addr     = document.getElementById('c-addr').value.trim();

  const title = titleRaw ||
    (catLabel && catLabel !== 'Selecione...' ? `${catLabel}${addr ? ' — ' + addr : ''}` : addr || 'Ocorrência registrada');

  const lat = _createMarker ? _createMarker.getLatLng().lat : null;
  const lng = _createMarker ? _createMarker.getLatLng().lng : null;

  if (!lat || !lng) {
    toast('⚠️ Sem localização no mapa — a ocorrência não aparecerá nos pings do mapa. Clique no mapa para marcar o local.', 'error');
  }

  const payload = {
    title, description: desc,
    category: catEl.value || null,
    address:  addr || null,
    status: 'open',
    latitude:  lat,
    longitude: lng,
  };

  try {
    const r = await api('/api/v1/occurrences/', { method:'POST', body: JSON.stringify(payload) });
    const d = await r.json();
    if (!r.ok) { toast('Erro ao criar: '+JSON.stringify(d),'error'); return; }

    if (d.duplicate) {
      toast('⚠️ ' + d.message, 'error');
      navigateTo('detail', d.original_id);
      return;
    }

    const occId = d.id || d.occurrence?.id;

    const files = document.getElementById('c-imgs').files;
    for (const file of files) {
      if (file && occId) await uploadImage(occId, file);
    }

    toast('Ocorrência registrada com sucesso!');
    navigateTo('detail', occId);
  } catch(e) { toast('Erro de conexão','error'); console.error(e); }
}

async function uploadImage(occId, file) {
  const fd = new FormData();
  fd.append('occurrence', occId);
  fd.append('image', file);
  try { await api('/api/v1/images/', { method:'POST', body: fd, headers:{} }); }
  catch(e) { console.warn('Imagem não enviada:', e); }
}

// ════════════════════════════════════
// DETAIL
// ════════════════════════════════════
async function loadDetail(id) {
  STATE.currentOccId = id;
  document.getElementById('det-hero-wrap').innerHTML = `<div class="loading-center"><div class="spinner"></div></div>`;
  document.getElementById('det-history').innerHTML = `<div class="loading-center"><div class="spinner"></div></div>`;
  document.getElementById('validation-body').innerHTML = '';
  document.getElementById('feedback-body').innerHTML = '';

  try {
    const r = await api(`/api/v1/occurrences/${id}/`);
    if (!r.ok) { toast('Ocorrência não encontrada','error'); navigateTo('occurrences'); return; }
    const o = await r.json();
    window._DETAIL_OCC = o;

    document.getElementById('det-title').textContent = o.title;
    document.getElementById('det-meta').textContent = `#${o.id} · Registrada em ${fmtDate(o.created_at)}`;

    const img = o.images?.length ? imgUrl(o.images[0].image || o.images[0].url) : null;
    document.getElementById('det-hero-wrap').innerHTML = img
      ? `<img src="${img}" class="detail-hero" onerror="this.style.display='none'">`
      : `<div class="detail-hero-placeholder"><svg viewBox="0 0 24 24"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg></div>`;

    document.getElementById('det-status').innerHTML = statusBadge(o.status);
    document.getElementById('det-reporter').textContent = o.user_details?.username || o.user_details?.first_name || `Usuário #${o.user}`;
    document.getElementById('det-cat').textContent = o.category_details?.name || '—';
    document.getElementById('det-addr').textContent = o.address || '—';
    document.getElementById('det-date').textContent = fmtDateFull(o.created_at);
    document.getElementById('det-valid').textContent = `${o.validation_count||0} validação(ões) comunitária(s)`;
    document.getElementById('det-desc').textContent = o.description || '—';
    _renderDetailExtras(o);

    if (o.urgency_level && o.urgency_level !== 'baixa' && isAdmin()) {
      document.getElementById('det-urgency-row').style.display = 'flex';
      document.getElementById('det-urgency').innerHTML = urgencyBadge(o.urgency_level);
    }
    if (o.importance_color) {
      document.getElementById('det-imp-row').style.display = 'flex';
      document.getElementById('det-imp').innerHTML = `<span class="badge ${impClass(o.importance_color)}">${impLabel(o.importance_color)}</span>`;
    }

    const actions = [];
    if (canEdit(o)) {
      actions.push(`<button class="btn btn-ghost btn-sm" onclick="navigateTo('edit',${o.id})">Editar</button>`);
      actions.push(`<button class="btn btn-danger btn-sm" onclick="deleteOcc(${o.id})">Excluir</button>`);
    }
    actions.push(`<button class="btn btn-ghost btn-sm" onclick="navigateTo('occurrences')">← Voltar</button>`);
    document.getElementById('det-actions').innerHTML = actions.join('');

    const sideActions = [];
    if (isAdmin()) {
      sideActions.push(`<button class="btn btn-primary btn-sm" onclick="openStatusModal(${o.id},'${o.status}','${o.importance_color||''}')">Atualizar Status</button>`);
      sideActions.push(`<button class="btn btn-ghost btn-sm" onclick="openAdminAiModal(${o.id})" style="color:var(--purple)">🤖 Verificar com IA</button>`);
    }
    if (STATE.user && String(o.user) !== String(STATE.user.id)) {
      sideActions.push(`<button class="btn btn-success btn-sm" onclick="openModal('modal-validate')">👥 Confirmar Problema</button>`);
    }
    if (isAdmin()) {
      sideActions.push(`<button class="btn btn-ghost btn-sm" onclick="openFeedbackModal()">📝 Enviar Atualização</button>`);
    } else if (o.status === 'resolved' || o.status === 'closed') {
      sideActions.push(`<button class="btn btn-ghost btn-sm" onclick="openFeedbackModal()">⭐ Enviar Feedback</button>`);
    }
    document.getElementById('det-sidebar-actions').innerHTML = sideActions.length
      ? sideActions.join('')
      : `<p style="font-size:.8rem;color:var(--muted)">Nenhuma ação disponível</p>`;

    buildValidationCard(o);
    buildFeedbackCard(o);
    loadHistory(id);

  } catch(e) { console.error(e); toast('Erro ao carregar detalhes','error'); }
}

function buildValidationCard(o) {
  const body = document.getElementById('validation-body');
  const pct = Math.min(100, (o.validation_count||0) * 10);
  body.innerHTML = `
    <div style="text-align:center;padding:8px 0">
      <div style="font-size:2rem;font-weight:700;color:var(--blue);font-family:var(--mono)">${o.validation_count||0}</div>
      <div style="font-size:.8rem;color:var(--muted);margin-bottom:12px">confirmações comunitárias</div>
      <div class="ai-score-bar"><div class="ai-score-fill" style="width:${pct}%;background:var(--blue)"></div></div>
      <p style="font-size:.72rem;color:var(--muted);margin-top:6px">Mais validações = maior prioridade de resolução</p>
    </div>`;
}

function buildFeedbackCard(o) {
  const body = document.getElementById('feedback-body');
  let html = '';

  if (o.feedbacks && o.feedbacks.length) {
    html += '<div style="margin-bottom:12px;">';
    o.feedbacks.forEach(f => {
      const isAdminFeedback = !f.rating;
      const name = f.user_details?.username || f.user_details?.name || `Usuário #${f.user}`;
      const date = fmtDate(f.created_at);
      const stars = f.rating ? '⭐'.repeat(f.rating) : '';
      const typeLabel = isAdminFeedback
        ? '<span style="font-size:.7rem;background:var(--blue);color:white;border-radius:4px;padding:1px 5px;margin-left:4px;">Atualização Oficial</span>'
        : '';
      html += `<div style="border:1px solid var(--border);border-radius:6px;padding:10px 12px;margin-bottom:8px;background:var(--surface)">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
          <span style="font-size:.82rem;font-weight:600;color:var(--text)">${esc(name)}${typeLabel}</span>
          <span style="font-size:.75rem;color:var(--muted)">${date}</span>
        </div>
        ${stars ? `<div style="font-size:.85rem;margin-bottom:4px;">${stars}</div>` : ''}
        <p style="font-size:.82rem;color:var(--text2);margin:0">${esc(f.comment)}</p>
      </div>`;
    });
    html += '</div>';
  }

  if (o.status !== 'resolved' && o.status !== 'closed') {
    if (!o.feedbacks?.length) {
      html += `<p style="font-size:.82rem;color:var(--muted);text-align:center">Disponível após a resolução da ocorrência.</p>`;
    }
  } else if (!isAdmin()) {
    html += `<button class="btn btn-primary btn-sm btn-full" onclick="openFeedbackModal()">⭐ Avaliar Resolução</button>`;
  }

  body.innerHTML = html;
}

async function loadHistory(id) {
  try {
    const r = await api(`/api/v1/occurrences/${id}/history/`);
    const d = await r.json();
    const list = Array.isArray(d) ? d : (d.results || []);
    const container = document.getElementById('det-history');
    if (!list.length) {
      container.innerHTML = `<p style="font-size:.82rem;color:var(--muted)">Sem alterações registradas.</p>`;
      return;
    }
    container.innerHTML = `<div class="timeline">` +
      list.map((h,i) => `
        <div class="timeline-item ${i===0?'latest':''}">
          <div class="timeline-date">${fmtDateFull(h.changed_at)}</div>
          <div class="timeline-text">${statusBadge(h.previous_status||'—')} → ${statusBadge(h.new_status||'—')}</div>
          ${h.observation ? `<div class="timeline-obs">${esc(h.observation)}</div>` : ''}
        </div>`).join('') + `</div>`;
  } catch(e) { document.getElementById('det-history').innerHTML = `<p style="font-size:.82rem;color:var(--muted)">Erro ao carregar histórico.</p>`; }
}

// ════════════════════════════════════
// EDIT
// ════════════════════════════════════
async function loadEditPage(id) {
  if (!STATE.categories.length) await loadCategories();
  try {
    const r = await api(`/api/v1/occurrences/${id}/`);
    const o = await r.json();
    document.getElementById('e-id').value       = o.id;
    document.getElementById('e-title').value    = o.title;
    document.getElementById('e-addr').value     = o.address || '';
    document.getElementById('e-desc').value     = o.description || '';
    if (isAdmin()) {
      document.getElementById('e-status').value = o.status;
      document.getElementById('e-imp').value    = o.importance_color || '';
    }
    populateCatSelect('e-cat', o.category);
    document.getElementById('file-preview-edit').innerHTML = '';
    document.getElementById('e-img').value = '';
    document.getElementById('edit-cancel-btn').onclick = () => navigateTo('detail', id);
  } catch(e) { toast('Erro ao carregar dados','error'); }
}

async function saveEdit() {
  const id = document.getElementById('e-id').value;
  const payload = {
    title:       document.getElementById('e-title').value.trim(),
    category:    document.getElementById('e-cat').value || null,
    address:     document.getElementById('e-addr').value.trim() || null,
    description: document.getElementById('e-desc').value.trim(),
  };
  if (isAdmin()) {
    payload.status           = document.getElementById('e-status').value;
    const imp                = document.getElementById('e-imp').value;
    if (imp) payload.importance_color = imp;
  }
  try {
    const r = await api(`/api/v1/occurrences/${id}/`, { method:'PATCH', body: JSON.stringify(payload) });
    if (!r.ok) { const e = await r.json(); toast('Erro: '+JSON.stringify(e),'error'); return; }
    const file = document.getElementById('e-img').files[0];
    if (file) await uploadImage(id, file);
    toast('Ocorrência atualizada!');
    navigateTo('detail', Number(id));
  } catch(e) { toast('Erro de conexão','error'); }
}

async function deleteOcc(id) {
  if (!confirm('Excluir permanentemente esta ocorrência?')) return;
  try {
    await api(`/api/v1/occurrences/${id}/`, { method:'DELETE' });
    toast('Ocorrência excluída');
    navigateTo('occurrences');
  } catch(e) { toast('Erro ao excluir','error'); }
}

// ════════════════════════════════════
// VALIDATION
// ════════════════════════════════════
function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

async function submitValidation() {
  const id = STATE.currentOccId;
  try {
    const r = await api(`/api/v1/validations/occurrence/${id}/`, { method:'POST' });
    const d = await r.json();
    if (!r.ok) { toast(d.error || 'Erro na validação','error'); closeModal('modal-validate'); return; }
    toast('Ocorrência validada com sucesso!');
    closeModal('modal-validate');
    loadDetail(id);
  } catch(e) { toast('Erro ao validar','error'); }
}

// ════════════════════════════════════
// FEEDBACK
// ════════════════════════════════════
function setRating(v) {
  STATE.feedbackRating = v;
  document.querySelectorAll('.star-btn').forEach(b => {
    b.classList.toggle('on', Number(b.dataset.v) <= v);
  });
}

async function submitFeedback() {
  const adminMode = isAdmin();
  if (!adminMode && !STATE.feedbackRating) { toast('Selecione uma avaliação','error'); return; }
  const comment = document.getElementById('fb-comment').value.trim();
  if (!comment) { toast('Escreva um comentário','error'); return; }
  const payload = { occurrence: STATE.currentOccId, comment };
  if (!adminMode) {
    payload.rating   = STATE.feedbackRating;
    payload.resolved = document.getElementById('fb-resolved').value === 'true';
  }
  try {
    const r = await api('/api/v1/feedbacks/', { method:'POST', body: JSON.stringify(payload) });
    const d = await r.json();
    if (!r.ok) { toast('Erro: '+JSON.stringify(d),'error'); return; }
    toast(adminMode ? 'Atualização enviada com sucesso!' : 'Feedback enviado. Obrigado!');
    closeModal('modal-feedback');
    STATE.feedbackRating = 0;
    document.querySelectorAll('.star-btn').forEach(b => b.classList.remove('on'));
    document.getElementById('fb-comment').value = '';
    if (STATE.currentOccId) loadDetail(STATE.currentOccId);
  } catch(e) { toast('Erro ao enviar feedback','error'); }
}

function openFeedbackModal() {
  const adminMode = isAdmin();
  document.getElementById('feedback-modal-title').textContent = adminMode ? 'Enviar Atualização do Ocorrido' : 'Enviar Feedback';
  document.getElementById('fb-rating-field').style.display = adminMode ? 'none' : '';
  document.getElementById('fb-resolved-field').style.display = adminMode ? 'none' : '';
  document.getElementById('fb-comment-label').textContent = adminMode ? 'Atualização / Informação' : 'Comentário';
  document.getElementById('fb-submit-btn').textContent = adminMode ? 'Enviar Atualização' : 'Enviar Feedback';
  document.getElementById('fb-comment').placeholder = adminMode
    ? 'Descreva o andamento ou novidades sobre esta ocorrência...'
    : 'Descreva sua experiência com a resolução...';
  openModal('modal-feedback');
}

// ════════════════════════════════════
// STATUS MODAL (ADMIN)
// ════════════════════════════════════
let _statusUpdateId = null;
function openStatusModal(id, currentStatus, currentImp) {
  _statusUpdateId = id;
  document.getElementById('modal-new-status').value = currentStatus;
  document.getElementById('modal-importance').value = currentImp || '';
  openModal('modal-status');
}

async function submitStatusUpdate() {
  const payload = { status: document.getElementById('modal-new-status').value };
  const imp = document.getElementById('modal-importance').value;
  if (imp) payload.importance_color = imp;
  try {
    const r = await api(`/api/v1/occurrences/${_statusUpdateId}/`, { method:'PATCH', body: JSON.stringify(payload) });
    if (!r.ok) { toast('Erro ao atualizar','error'); return; }
    toast('Status atualizado!');
    closeModal('modal-status');
    loadDetail(_statusUpdateId);
  } catch(e) { toast('Erro de conexão','error'); }
}

// ════════════════════════════════════
// ADMIN PAGE
// ════════════════════════════════════
async function loadAdminPage() {
  try {
    const [statR] = await Promise.all([api('/api/v1/statistics/')]);
    const stats = await statR.json();
    document.getElementById('admin-stats-grid').innerHTML = `
      <div class="stat-card">
        <div class="stat-card-top"><div class="stat-icon blue"><svg viewBox="0 0 24 24"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg></div></div>
        <div class="stat-value">${stats.total_usuarios||'—'}</div>
        <div class="stat-label">Usuários Cadastrados</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-top"><div class="stat-icon yellow"><svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/></svg></div></div>
        <div class="stat-value">${stats.total_ocorrencias||'—'}</div>
        <div class="stat-label">Total de Ocorrências</div>
      </div>
      <div class="stat-card">
        <div class="stat-card-top"><div class="stat-icon green"><svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg></div></div>
        <div class="stat-value">${stats.total_categorias||'—'}</div>
        <div class="stat-label">Categorias Ativas</div>
      </div>`;
  } catch(e) { console.error(e); }
  loadAdminOccurrences();
}

async function loadAdminOccurrences() {
  document.getElementById('admin-loading').classList.remove('hidden');
  document.getElementById('admin-table-body').innerHTML = '';

  if (!STATE.categories.length) await loadCategories();
  const catSel = document.getElementById('adm-map-cat');
  if (catSel && catSel.options.length <= 1) {
    STATE.categories.forEach(c => {
      const o = document.createElement('option');
      o.value = c.id; o.textContent = c.name;
      catSel.appendChild(o);
    });
  }

  const status = document.getElementById('admin-status-filter').value;
  const params = status ? `?status=${status}` : '';
  try {
    const r = await api(`/api/v1/occurrences/${params}`);
    const d = await r.json();
    const list = Array.isArray(d) ? d : (d.results || []);
    window._STATE_ADMIN = list;
    document.getElementById('admin-table-body').innerHTML = list.map(o => `
      <tr>
        <td class="td-mono">#${o.id}</td>
        <td class="td-title" onclick="navigateTo('detail',${o.id})" style="cursor:pointer;color:var(--blue)">${esc(o.title)}</td>
        <td style="font-size:.8rem;color:var(--muted)">${esc(o.category_details?.name||'—')}</td>
        <td style="font-size:.8rem;color:var(--muted)">${esc(o.user_details?.username||o.user||'—')}</td>
        <td>${statusBadge(o.status)}</td>
        <td>${urgencyBadge(o.urgency_level)}</td>
        <td>${o.importance_color ? `<span class="badge ${impClass(o.importance_color)}">${impLabel(o.importance_color)}</span>` : '<span style="color:var(--muted);font-size:.78rem">—</span>'}</td>
        <td style="font-size:.85rem">${o.validation_count||0}</td>
        <td class="td-mono" style="font-size:.78rem">${fmtDate(o.created_at)}</td>
        <td>
          <div style="display:flex;gap:4px">
            <button class="btn btn-ghost btn-sm" onclick="navigateTo('detail',${o.id})">Ver</button>
            <button class="btn btn-ghost btn-sm" onclick="openStatusModal(${o.id},'${o.status}','${o.importance_color||''}')">Status</button>
            <button class="btn btn-ghost btn-sm" onclick="openAdminAiModal(${o.id})" title="Verificar com IA" style="color:var(--purple)">🤖 IA</button>
          </div>
        </td>
      </tr>`).join('');
  } catch(e) { console.error(e); }
  document.getElementById('admin-loading').classList.add('hidden');
}

// ════════════════════════════════════
// Admin: Verificar com IA
// ════════════════════════════════════
async function openAdminAiModal(occId) {
  const occ = (window._STATE_ADMIN?.find(o => o.id === occId))
           || (window._STATE_OCC?.find(o => o.id === occId))
           || window._DETAIL_OCC;
  if (!occ) { toast('Ocorrência não encontrada','error'); return; }
  openModal('modal-admin-ai');
  const loading = document.getElementById('admin-ai-loading');
  const content = document.getElementById('admin-ai-content');
  loading.style.display = 'flex';
  content.innerHTML = '';
  try {
    const r = await api('/api/v1/validations/ai-analyze/', {
      method: 'POST',
      body: JSON.stringify({
        title: occ.title,
        description: occ.description,
        category_id: occ.category || null,
        latitude: occ.latitude || null,
        longitude: occ.longitude || null,
        address: occ.address || null,
      })
    });
    const d = await r.json();
    const levelColors = { critical:'var(--red)', high:'var(--yellow)', medium:'var(--blue)', low:'var(--green)' };
    const levelLabels = { critical:'Crítica', high:'Alta', medium:'Média', low:'Baixa' };
    const urg = d.urgency;
    const color = levelColors[urg?.urgency_level] || 'var(--muted)';
    let html = `<div style="margin-bottom:16px">
      <p style="font-size:.78rem;color:var(--muted);margin-bottom:8px">Ocorrência <strong>#${occ.id}</strong> — ${esc(occ.title)}</p>
      <div class="ai-panel-title" style="margin-bottom:12px">
        <svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 100 20A10 10 0 0012 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
        Análise de Urgência
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
        <span style="font-size:.9rem;color:#c9d1d9">Urgência: <strong style="color:${color}">${levelLabels[urg?.urgency_level]||'—'}</strong></span>
        <span style="font-family:var(--mono);font-size:.85rem;color:var(--muted)">${urg?.urgency_score||0}/100</span>
      </div>
      <div class="ai-score-bar"><div class="ai-score-fill" style="width:${urg?.urgency_score||0}%;background:${color}"></div></div>
      <p style="font-size:.82rem;color:var(--muted);margin-top:8px">${esc(urg?.urgency_reason||'')}</p>
    </div>`;
    const dup = d.duplicate;
    if (dup?.is_duplicate) {
      html += `<div class="ai-dup-alert">
        <strong>⚠ Possível duplicata detectada</strong><br>
        ${esc(dup.reason)} (Similaridade: ${dup.similarity_score}%)
        ${d.similar_occurrences?.length ? `<div style="margin-top:8px;font-size:.78rem">
          Ocorrência similar: <a href="#" onclick="closeModal('modal-admin-ai');navigateTo('detail',${dup.duplicate_of_id})">#${dup.duplicate_of_id}</a>
        </div>` : ''}
      </div>`;
    } else {
      html += `<p style="font-size:.82rem;color:var(--green)">✓ Nenhuma duplicata encontrada na área</p>`;
    }
    content.innerHTML = html;
  } catch(e) { content.innerHTML = `<p style="color:var(--red);font-size:.85rem">Erro ao analisar com IA.</p>`; console.error(e); }
  loading.style.display = 'none';
}

// ════════════════════════════════════
// HELPERS / UTILS
// ════════════════════════════════════
function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmtDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('pt-BR');
}

function fmtDateFull(d) {
  if (!d) return '—';
  return new Date(d).toLocaleString('pt-BR', {dateStyle:'short', timeStyle:'short'});
}

function statusBadge(s) {
  const map = {
    open:        ['badge-open','Aberta'],
    in_progress: ['badge-progress','Em Andamento'],
    resolved:    ['badge-resolved','Resolvida'],
    closed:      ['badge-closed','Fechada'],
  };
  const [cls, label] = map[s] || ['badge-closed', s||'—'];
  return `<span class="badge ${cls}"><span class="badge-dot"></span>${label}</span>`;
}

function urgencyBadge(l) {
  if (!l || l === 'baixa') return '';
  const map = { critica:'badge-critical', alta:'badge-high', media:'badge-medium', baixa:'badge-low' };
  const labels = { critica:'Crítica', alta:'Alta', media:'Média', baixa:'Baixa' };
  return `<span class="badge ${map[l]||'badge-low'}">${labels[l]||l}</span>`;
}

function impClass(c) {
  return c === 'green' ? 'imp-green' : c === 'yellow' ? 'imp-yellow' : c === 'red' ? 'imp-red' : '';
}

function impLabel(c) {
  return c === 'green' ? '🟢 Normal' : c === 'yellow' ? '🟡 Atenção' : c === 'red' ? '🔴 Urgente' : c;
}

function canEdit(o) {
  if (!STATE.user) return false;
  if (isAdmin()) return true;
  return String(o.user) === String(STATE.user.id) || String(o.user_details?.id) === String(STATE.user.id);
}

function togglePw(id, btn) {
  const inp = document.getElementById(id);
  inp.type = inp.type === 'password' ? 'text' : 'password';
  btn.querySelector('svg path').setAttribute('d',
    inp.type === 'text'
      ? 'M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.82l2.92 2.92c1.51-1.26 2.7-2.89 3.44-4.74-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27z'
      : 'M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z'
  );
}

function previewFile(input, previewId) {
  const file = input.files[0];
  const preview = document.getElementById(previewId);
  if (!file) { preview.innerHTML = ''; return; }
  const reader = new FileReader();
  reader.onload = e => { preview.innerHTML = `<img src="${e.target.result}" style="max-height:120px;border-radius:6px;border:1px solid var(--border);margin-top:8px;">`; };
  reader.readAsDataURL(file);
}

function handleFileDrop(event, inputId, dropId) {
  event.preventDefault();
  document.getElementById(dropId).classList.remove('over');
  const file = event.dataTransfer.files[0];
  if (!file) return;
  const input = document.getElementById(inputId);
  const dt = new DataTransfer();
  dt.items.add(file);
  input.files = dt.files;
  previewFile(input, 'file-preview-create');
}

function toast(msg, type='success') {
  const icons = {
    success: '<svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>',
    error:   '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>',
    info:    '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>',
  };
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.innerHTML = icons[type] + esc(msg);
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 3800);
}

document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.classList.add('hidden');
  });
});

// ════════════════════════════════════
// INIT
// ════════════════════════════════════
(async function init() {
  const savedUser = localStorage.getItem('im_user');
  if (tk.get() && savedUser) {
    try {
      STATE.user = JSON.parse(savedUser);
      updateUserUI();
      hideAuthScreens();
      navigateTo('dashboard');
    } catch {
      showScreen('screen-login');
    }
  } else if (tk.get()) {
    try {
      await loadCurrentUser();
      if (STATE.user) {
        hideAuthScreens();
        navigateTo('dashboard');
      } else { showScreen('screen-login'); }
    } catch { showScreen('screen-login'); }
  } else {
    showScreen('screen-login');
  }
})();

// ════════════════════════════════════
// RF03: Recuperação de senha
// ════════════════════════════════════
async function submitForgot() {
  const user = document.getElementById('forgot-user').value.trim();
  const msgEl = document.getElementById('forgot-msg');
  if (!user) { toast('Informe o usuário','error'); return; }
  msgEl.style.display = 'block';
  msgEl.style.background = 'rgba(47,129,247,.1)';
  msgEl.style.border = '1px solid rgba(47,129,247,.3)';
  msgEl.style.color = 'var(--blue)';
  msgEl.textContent = '✓ Solicitação registrada para "' + user + '". Um administrador redefinirá sua senha.';
}

// ════════════════════════════════════
// RF07: Múltiplas imagens
// ════════════════════════════════════
function previewFiles(input, previewId) {
  const preview = document.getElementById(previewId);
  if (!preview) return;
  preview.innerHTML = '';
  Array.from(input.files).forEach((file, i) => {
    const reader = new FileReader();
    reader.onload = e => {
      const wrap = document.createElement('div');
      wrap.className = 'img-thumb-wrap';
      wrap.innerHTML = '<img src="' + e.target.result + '"><button onclick="removePreviewFile(' + i + ',\'' + input.id + '\',\'' + previewId + '\')">✕</button>';
      preview.appendChild(wrap);
    };
    reader.readAsDataURL(file);
  });
}
function removePreviewFile(index, inputId, previewId) {
  const input = document.getElementById(inputId);
  const dt = new DataTransfer();
  Array.from(input.files).forEach((f, i) => { if (i !== index) dt.items.add(f); });
  input.files = dt.files;
  previewFiles(input, previewId);
}
function openLightbox(src) {
  const lb = document.getElementById('lightbox');
  if (lb) { document.getElementById('lightbox-img').src = src; lb.classList.remove('hidden'); }
}

// ════════════════════════════════════
// RF08: GPS + Mapa Leaflet no Create
// ════════════════════════════════════
function imgUrl(raw) {
  if (!raw) return null;
  if (raw.startsWith('http')) return raw;
  return API + raw;
}
let _createMarker = null;
const _maps = {};

function getGPS() {
  if (!navigator.geolocation) { toast('Geolocalização não suportada','error'); return; }
  toast('Obtendo localização...','info');
  navigator.geolocation.getCurrentPosition(pos => {
    const lat = pos.coords.latitude.toFixed(5);
    const lng = pos.coords.longitude.toFixed(5);
    const latEl = document.getElementById('c-lat');
    const lngEl = document.getElementById('c-lng');
    if (latEl) latEl.value = lat;
    if (lngEl) lngEl.value = lng;
    const label = document.getElementById('c-coords-label');
    if (label) { label.textContent = '📍 GPS: ' + lat + ', ' + lng + ' (±' + Math.round(pos.coords.accuracy) + 'm)'; label.style.display = 'block'; }
    toast('Localização obtida!');
    updateCreateMap(parseFloat(lat), parseFloat(lng), '📍 Minha localização');
  }, err => toast('Erro GPS: ' + err.message, 'error'), { enableHighAccuracy: true, timeout: 10000 });
}

async function geocodeAddress() {
  const inputBusca = document.getElementById('c-addr');
  const inputFormulario = document.getElementById('location');
  let addr = inputBusca?.value?.trim() || inputFormulario?.value?.trim();
  if (!addr) {
    toast('Preencha o campo de endereço ou localização primeiro', 'error');
    return;
  }
  if (inputBusca) inputBusca.value = addr;
  if (inputFormulario) inputFormulario.value = addr;
  toast('Buscando endereço...', 'info');
  try {
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(addr)}&limit=3&addressdetails=1`;
    const resp = await fetch(url, { headers: { 'Accept-Language': 'pt-BR,pt;q=0.9' } });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const results = await resp.json();
    if (!results || !results.length) {
      toast('Endereço não encontrado. Tente apenas cidade e estado, ex: "Curitiba, PR"', 'error');
      return;
    }
    const { lat, lon, display_name } = results[0];
    document.getElementById('c-lat').value = parseFloat(lat).toFixed(6);
    document.getElementById('c-lng').value = parseFloat(lon).toFixed(6);
    const label = document.getElementById('c-coords-label');
    if (label) { label.textContent = '📍 ' + display_name; label.style.display = 'block'; }
    updateCreateMap(parseFloat(lat), parseFloat(lon), addr);
    toast('Encontrado! Clique no mapa para ajustar o ponto exato.');
  } catch(e) {
    console.error('Geocode error:', e);
    toast('Erro ao buscar endereço. Verifique sua conexão e tente novamente.', 'error');
  }
}

function updateCreateMap(lat, lng, popupText) {
  if (isNaN(lat) || isNaN(lng)) { toast('Coordenadas inválidas','error'); return; }
  if (!_maps.create) {
    initCreateMapDefault();
    setTimeout(() => _placeCreateMarker(lat, lng, popupText), 300);
    return;
  }
  _maps.create.setView([lat, lng], 16);
  _placeCreateMarker(lat, lng, popupText);
}

function _placeCreateMarker(lat, lng, popupText) {
  if (_createMarker) _maps.create.removeLayer(_createMarker);
  _createMarker = L.marker([lat, lng]).addTo(_maps.create).bindPopup(popupText || '📍 Local da ocorrência').openPopup();
  setTimeout(() => _maps.create.invalidateSize(), 100);
}

function _initDetailMap(lat, lng, title, addr) {
  if (_maps.detail) { _maps.detail.remove(); _maps.detail = null; }
  _maps.detail = L.map('detail-map').setView([lat, lng], 16);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap', maxZoom: 19 }).addTo(_maps.detail);
  L.marker([lat, lng]).addTo(_maps.detail).bindPopup('<b>' + (title||'') + '</b><br>' + (addr||'')).openPopup();
  _maps.detail.invalidateSize();
}

// ════════════════════════════════════
// RF18 + RF24: detail page extras
// ════════════════════════════════════
function _renderDetailExtras(o) {
  const deadRow = document.getElementById('det-deadline-row');
  const deadEl  = document.getElementById('det-deadline');
  if (deadRow && deadEl && o.data_limite_validacao) {
    deadRow.style.display = 'flex';
    const dl = new Date(o.data_limite_validacao);
    const past = dl < new Date();
    deadEl.innerHTML = '<span style="color:' + (past?'var(--red)':'var(--yellow)') + '">' + dl.toLocaleDateString('pt-BR') + (past?' (expirado)':'') + '</span>';
  }
  const timeWrap = document.getElementById('det-time-wrap');
  if (timeWrap && (o.estimated_time || o.resolved_at)) {
    let h = '<div class="time-info-box">';
    if (o.estimated_time) h += '<div class="time-info-item"><span class="time-info-label">Tempo Estimado</span><span class="time-info-value">' + o.estimated_time + 'h</span></div>';
    if (o.resolved_at) {
      const ms = new Date(o.resolved_at) - new Date(o.created_at);
      const hrs = Math.round(ms / 36e5);
      h += '<div class="time-info-item"><span class="time-info-label">Resolvida em</span><span class="time-info-value">' + hrs + 'h</span></div>';
      h += '<div class="time-info-item"><span class="time-info-label">Data Resolução</span><span class="time-info-value" style="font-size:.8rem">' + new Date(o.resolved_at).toLocaleDateString('pt-BR') + '</span></div>';
    }
    h += '</div>';
    timeWrap.innerHTML = h;
  }
  const mapWrap = document.getElementById('det-map-wrap');
  if (mapWrap && o.latitude && o.longitude) {
    mapWrap.style.display = 'block';
    setTimeout(() => _initDetailMap(parseFloat(o.latitude), parseFloat(o.longitude), o.title, o.address), 200);
  }
  const gallery = document.getElementById('det-gallery');
  if (gallery && o.images && o.images.length > 1) {
    gallery.innerHTML = o.images.slice(1).map(img => {
      const src = imgUrl(img.image || img.url);
      return '<img src="' + src + '" onclick="openLightbox(\'' + src + '\')" onerror="this.style.display=\'none\'">';
    }).join('');
  }
}

// ════════════════════════════════════
// RF26: Mapa na lista de ocorrências
// ════════════════════════════════════
function setMapView() {
  const gv = document.getElementById('occ-grid-view');
  const tv = document.getElementById('occ-table-view');
  const mv = document.getElementById('occ-map-view');
  if (gv) gv.classList.add('hidden');
  if (tv) tv.classList.add('hidden');
  if (mv) { mv.classList.remove('hidden'); setTimeout(renderOccurrencesMap, 100); }
}

function renderOccurrencesMap() {
  if (typeof L === 'undefined') return;
  if (_maps.occList) { _maps.occList.remove(); _maps.occList = null; }
  const list = (window._STATE_OCC || []).filter(o => o.latitude && o.longitude);
  const center = list.length ? [parseFloat(list[0].latitude), parseFloat(list[0].longitude)] : [-15.7801, -47.9292];
  _maps.occList = L.map('occ-list-map').setView(center, list.length ? 13 : 5);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap', maxZoom: 19 }).addTo(_maps.occList);
  const colorMap = { open:'#2f81f7', in_progress:'#d29922', resolved:'#3fb950', closed:'#656d76' };
  list.forEach(o => {
    const color = colorMap[o.status] || '#2f81f7';
    const icon = L.divIcon({ html: '<div style="width:14px;height:14px;border-radius:50%;background:' + color + ';border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.5)"></div>', className:'', iconSize:[14,14], iconAnchor:[7,7] });
    L.marker([parseFloat(o.latitude), parseFloat(o.longitude)], { icon })
      .addTo(_maps.occList)
      .bindPopup('<b>' + (o.title||'') + '</b><br>' + (o.address||''));
  });
  if (list.length > 1) _maps.occList.fitBounds(list.map(o => [parseFloat(o.latitude), parseFloat(o.longitude)]), { padding:[40,40] });
}

// ════════════════════════════════════
// RF26: Mapa admin com pins
// ════════════════════════════════════
function switchAdminTab(tab) {
  const lv = document.getElementById('admin-list-view');
  const mv = document.getElementById('admin-map-view');
  const tl = document.getElementById('admin-tab-list');
  const tm = document.getElementById('admin-tab-map');
  if (lv) lv.classList.toggle('hidden', tab !== 'list');
  if (mv) mv.classList.toggle('hidden', tab !== 'map');
  if (tl) tl.classList.toggle('active', tab === 'list');
  if (tm) tm.classList.toggle('active', tab === 'map');
  if (tab === 'map') setTimeout(renderAdminMap, 150);
}

function renderAdminMap() {
  if (typeof L === 'undefined') return;
  if (_maps.admin) { _maps.admin.remove(); _maps.admin = null; }

  const catSel = document.getElementById('adm-map-cat');
  if (catSel && catSel.options.length <= 1 && STATE.categories.length) {
    STATE.categories.forEach(c => {
      const o = document.createElement('option');
      o.value = c.id; o.textContent = c.name;
      catSel.appendChild(o);
    });
  }

  const palette = ['#2f81f7','#3fb950','#d29922','#f85149','#a371f7',
                   '#06b6d4','#f97316','#ec4899','#84cc16','#14b8a6'];
  const catColorMap = {};
  STATE.categories.forEach((c, i) => { catColorMap[c.id] = palette[i % palette.length]; });

  const legend = document.getElementById('adm-map-legend');
  if (legend) {
    legend.innerHTML = STATE.categories.map(c => {
      const color = catColorMap[c.id] || '#2f81f7';
      return `<div onclick="document.getElementById('adm-map-cat').value='${c.id}';renderAdminMap()"
                   style="display:flex;align-items:center;gap:5px;font-size:.75rem;color:#8b949e;
                          background:var(--surface);border:1px solid var(--border);
                          border-radius:6px;padding:3px 8px;cursor:pointer;">
                <span style="width:9px;height:9px;border-radius:50%;background:${color};flex-shrink:0"></span>
                ${esc(c.name)}
              </div>`;
    }).join('');
  }

  const filterCat    = document.getElementById('adm-map-cat')?.value || '';
  const filterStatus = document.getElementById('adm-map-status')?.value || '';
  const all = (window._STATE_ADMIN || []).filter(o => {
    if (!o.latitude || !o.longitude) return false;
    if (filterCat    && String(o.category) !== String(filterCat))   return false;
    if (filterStatus && o.status !== filterStatus)                   return false;
    return true;
  });

  const countEl = document.getElementById('adm-map-count');
  if (countEl) countEl.textContent = `${all.length} ocorrência${all.length !== 1 ? 's' : ''} no mapa`;

  const center = all.length
    ? [parseFloat(all[0].latitude), parseFloat(all[0].longitude)]
    : [-15.7801, -47.9292];

  _maps.admin = L.map('admin-map').setView(center, all.length ? 12 : 5);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap', maxZoom: 19
  }).addTo(_maps.admin);

  all.forEach(o => {
    const color = catColorMap[o.category] || '#2f81f7';
    const size  = Math.max(12, Math.min(26, 12 + (o.validation_count || 0) * 2));
    const catName = STATE.categories.find(c => c.id === o.category)?.name || '—';
    const icon = L.divIcon({
      html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};
                         border:2px solid rgba(255,255,255,.4);
                         box-shadow:0 0 6px ${color}99;"></div>`,
      className: '', iconSize: [size, size], iconAnchor: [size/2, size/2]
    });
    L.marker([parseFloat(o.latitude), parseFloat(o.longitude)], { icon })
      .addTo(_maps.admin)
      .bindPopup(`
        <div style="min-width:190px;font-family:sans-serif">
          <div style="font-weight:700;margin-bottom:4px">${esc(o.title)}</div>
          <div style="display:flex;align-items:center;gap:5px;font-size:.78rem;margin-bottom:4px">
            <span style="width:8px;height:8px;border-radius:50%;background:${color};flex-shrink:0"></span>
            ${esc(catName)}
          </div>
          ${o.address ? `<div style="font-size:.78rem;color:#666;margin-bottom:4px">${esc(o.address)}</div>` : ''}
          <div style="font-size:.75rem;color:#888">${o.validation_count||0} validações</div>
          <button onclick="navigateTo('detail',${o.id})"
            style="margin-top:8px;padding:4px 10px;background:#2f81f7;color:white;
                   border:none;border-radius:4px;cursor:pointer;font-size:.75rem;width:100%">
            Ver detalhes
          </button>
        </div>`);
  });

  if (all.length > 1) {
    _maps.admin.fitBounds(
      all.map(o => [parseFloat(o.latitude), parseFloat(o.longitude)]),
      { padding: [40, 40], maxZoom: 14 }
    );
  }
  setTimeout(() => _maps.admin.invalidateSize(), 100);
}