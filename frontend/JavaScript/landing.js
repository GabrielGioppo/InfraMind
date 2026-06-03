
// ============================================================
// Landing — InfraMind
// ============================================================
const API = 'http://127.0.0.1:9000';
const ANON_KEY = 'im_anon_id';
const ANON_OCCS_KEY = 'im_anon_occs';

// ══════════════════════════════════════════
// TOKEN & SESSION
// ══════════════════════════════════════════
const tk = {
  get:    () => localStorage.getItem('im_access'),
  getRef: () => localStorage.getItem('im_refresh'),
  set:    (a, r) => { localStorage.setItem('im_access', a); if (r) localStorage.setItem('im_refresh', r); },
  clear:  () => ['im_access','im_refresh','im_user'].forEach(k => localStorage.removeItem(k)),
  user:   () => { try { return JSON.parse(localStorage.getItem('im_user')); } catch { return null; } },
  setUser:(u) => localStorage.setItem('im_user', JSON.stringify(u)),
};

function getAnonId() {
  let id = localStorage.getItem(ANON_KEY);
  if (!id) {
    id = 'anon-' + Date.now() + '-' + Math.random().toString(36).slice(2, 9);
    localStorage.setItem(ANON_KEY, id);
  }
  return id;
}

function getAnonOccs() {
  try { return JSON.parse(localStorage.getItem(ANON_OCCS_KEY) || '[]'); } catch { return []; }
}
function saveAnonOcc(occ) {
  const list = getAnonOccs();
  list.push({ ...occ, _saved_at: Date.now() });
  localStorage.setItem(ANON_OCCS_KEY, JSON.stringify(list));
}
function clearAnonOccs() {
  localStorage.removeItem(ANON_OCCS_KEY);
}

async function claimAnonOccurrences() {
  const anonOccs = getAnonOccs();
  if (anonOccs.length === 0) return;
  const anonId = getAnonId();
  try {
    const r = await apiFetch('/api/v1/occurrences/anonymous/claim/', {
      method: 'POST',
      body: JSON.stringify({ anon_id: anonId }),
    });
    if (r.ok) {
      const d = await r.json();
      clearAnonOccs();
      if (d.claimed > 0) {
        toast(`✓ ${d.claimed} ocorrência${d.claimed > 1 ? 's' : ''} vinculada${d.claimed > 1 ? 's' : ''} à sua conta!`, 'success');
      }
    }
  } catch {}
}

// ══════════════════════════════════════════
// API FETCH WRAPPER
// ══════════════════════════════════════════
async function apiFetch(path, opts = {}) {
  const hdrs = { ...opts.headers };
  if (tk.get()) hdrs['Authorization'] = `Bearer ${tk.get()}`;
  if (!(opts.body instanceof FormData)) hdrs['Content-Type'] = 'application/json';
  let res = await fetch(`${API}${path}`, { ...opts, headers: hdrs });
  if (res.status === 401 && tk.getRef()) {
    const ok = await refreshToken();
    if (ok) {
      hdrs['Authorization'] = `Bearer ${tk.get()}`;
      res = await fetch(`${API}${path}`, { ...opts, headers: hdrs });
    }
  }
  return res;
}

async function refreshToken() {
  try {
    const r = await fetch(`${API}/authentication/token/refresh/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: tk.getRef() })
    });
    if (!r.ok) return false;
    const d = await r.json();
    tk.set(d.access);
    return true;
  } catch { return false; }
}

// ══════════════════════════════════════════
// OBTER TOKENS — username OU e-mail
// ══════════════════════════════════════════
async function fetchTokens(usernameOrEmail, password) {
  // Tenta como username primeiro
  const r1 = await fetch(`${API}/authentication/token/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: usernameOrEmail, password })
  });
  if (r1.ok) return await r1.json();

  // Tenta como e-mail (endpoint dedicado que retorna os mesmos tokens)
  const r2 = await fetch(`${API}/authentication/login/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: usernameOrEmail, password })
  });
  if (r2.ok) return await r2.json();

  return null;
}

// ══════════════════════════════════════════
// SALVA O USUÁRIO LOGADO NO localStorage
// Decodifica o JWT para obter o user_id e
// busca /api/v1/users/<id>/ diretamente
// (funciona para qualquer perfil).
// ══════════════════════════════════════════
async function loadAndStoreUser() {
  try {
    const payload = JSON.parse(atob(tk.get().split('.')[1]));
    const userId  = payload.user_id;
    // Busca o perfil do próprio usuário pelo ID
    const r = await apiFetch(`/api/v1/users/${userId}/`);
    if (r.ok) {
      const me = await r.json();
      tk.setUser(me);
      return me;
    }
    // Fallback: lista todos (funciona se for admin)
    const r2 = await apiFetch('/api/v1/users/');
    if (r2.ok) {
      const d = await r2.json();
      const users = Array.isArray(d) ? d : (d.results || []);
      const me2 = users.find(u => u.id === userId);
      if (me2) { tk.setUser(me2); return me2; }
    }
  } catch {}
  return null;
}

// ══════════════════════════════════════════
// STATS
// ══════════════════════════════════════════
async function loadStats() {
  try {
    const r = await fetch(`${API}/api/v1/statistics/`);
    if (!r.ok) return;
    const d = await r.json();
    animateCount('stat-ocorrencias', d.total_ocorrencias ?? 0);
    animateCount('stat-usuarios', d.total_usuarios ?? 0);
    animateCount('stat-cats', d.total_categorias ?? 0);
  } catch (e) {
    console.error('Erro ao buscar estatísticas:', e);
  }
}

function animateCount(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  let cur = 0;
  const step = Math.ceil(target / 40);
  const t = setInterval(() => {
    cur = Math.min(cur + step, target);
    el.textContent = cur.toLocaleString('pt-BR');
    if (cur >= target) clearInterval(t);
  }, 30);
}

// ══════════════════════════════════════════
// MODAL UTILS
// ══════════════════════════════════════════
function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

document.querySelectorAll('.modal-overlay').forEach(o => {
  o.addEventListener('click', e => { if (e.target === o) o.classList.remove('open'); });
});

// ══════════════════════════════════════════
// AUTH MODAL
// ══════════════════════════════════════════
function openAuthModal(tab) {
  switchAuthTab(tab);
  openModal('modal-auth');
}

function switchAuthTab(tab) {
  document.getElementById('tab-login').classList.toggle('active', tab === 'login');
  document.getElementById('tab-register').classList.toggle('active', tab === 'register');
  document.getElementById('pane-login').classList.toggle('active', tab === 'login');
  document.getElementById('pane-register').classList.toggle('active', tab === 'register');

  const anonBanner = document.getElementById('anon-merge-banner');
  if (anonBanner) {
    anonBanner.style.display = (tab === 'register' && getAnonOccs().length > 0) ? 'flex' : 'none';
  }
}

function togglePw(id, btn) {
  const inp = document.getElementById(id);
  const isText = inp.type === 'text';
  inp.type = isText ? 'password' : 'text';
  const path = btn.querySelector('svg path');
  if (path) {
    path.setAttribute('d', isText
      ? 'M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z'
      : 'M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.82l2.92 2.92c1.51-1.26 2.7-2.89 3.44-4.74-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27z'
    );
  }
}

// ══════════════════════════════════════════
// VALIDAÇÃO DO CAMPO USERNAME EM TEMPO REAL
// Bloqueia espaços e caracteres inválidos.
// ══════════════════════════════════════════
function initUsernameField(inputId, errorId) {
  const input = document.getElementById(inputId);
  const errorEl = document.getElementById(errorId);
  if (!input) return;

  input.addEventListener('keydown', e => {
    if (e.key === ' ') { e.preventDefault(); }
  });

  input.addEventListener('input', () => {
    // Remove qualquer caractere inválido que tenha sido colado
    const clean = input.value.replace(/[^a-zA-Z0-9_]/g, '');
    if (input.value !== clean) input.value = clean;

    if (!errorEl) return;
    if (input.value.length > 0 && !/^[a-zA-Z0-9_]+$/.test(input.value)) {
      errorEl.textContent = 'Apenas letras, números e _ são permitidos. Sem espaços.';
      errorEl.style.display = 'block';
    } else {
      errorEl.style.display = 'none';
    }
  });

  input.addEventListener('paste', e => {
    e.preventDefault();
    const pasted = (e.clipboardData || window.clipboardData).getData('text');
    const clean  = pasted.replace(/[^a-zA-Z0-9_]/g, '');
    const start  = input.selectionStart;
    const end    = input.selectionEnd;
    input.value  = input.value.slice(0, start) + clean + input.value.slice(end);
    input.dispatchEvent(new Event('input'));
  });
}

// ══════════════════════════════════════════
// LOGIN
// ══════════════════════════════════════════
async function doLogin() {
  const usernameOrEmail = document.getElementById('auth-username').value.trim();
  const password = document.getElementById('auth-password').value;
  const msgEl = document.getElementById('login-msg');
  msgEl.innerHTML = '';

  if (!usernameOrEmail || !password) {
    msgEl.innerHTML = '<div class="msg msg-error">Preencha usuário/e-mail e senha.</div>';
    return;
  }

  try {
    msgEl.innerHTML = '<div class="msg msg-info">Autenticando...</div>';
    const tokens = await fetchTokens(usernameOrEmail, password);

    if (!tokens) {
      msgEl.innerHTML = '<div class="msg msg-error">Credenciais inválidas. Verifique e tente novamente.</div>';
      return;
    }

    tk.set(tokens.access, tokens.refresh);
    const me = await loadAndStoreUser();
    await claimAnonOccurrences();
    closeModal('modal-auth');
    toast('Bem-vindo de volta!', 'success');
    updateNavbar(me);
  } catch (err) {
    console.error(err);
    msgEl.innerHTML = '<div class="msg msg-error">Erro de conexão com o servidor.</div>';
  }
}

// ══════════════════════════════════════════
// REGISTER — auto-login, sem redirecionar
// ══════════════════════════════════════════
async function doRegister() {
  const username = document.getElementById('reg-username').value.trim();
  const email    = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  const msgEl    = document.getElementById('register-msg');
  msgEl.innerHTML = '';

  if (!username || !email || !password) {
    msgEl.innerHTML = '<div class="msg msg-error">Preencha todos os campos obrigatórios.</div>';
    return;
  }
  if (!/^[a-zA-Z0-9_]+$/.test(username)) {
    msgEl.innerHTML = '<div class="msg msg-error">O usuário só pode conter letras, números e _. Sem espaços.</div>';
    return;
  }
  if (password.length < 8) {
    msgEl.innerHTML = '<div class="msg msg-error">A senha precisa ter pelo menos 8 caracteres.</div>';
    return;
  }

  const payload = { username, email, password };

  try {
    msgEl.innerHTML = '<div class="msg msg-info">Criando sua conta...</div>';
    const r = await fetch(`${API}/api/v1/users/register/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const d = await r.json();
    if (!r.ok) {
      const detail = d.email?.[0] || d.username?.[0] || JSON.stringify(d);
      msgEl.innerHTML = `<div class="msg msg-error">Erro no cadastro: ${detail}</div>`;
      return;
    }

    // Auto-login com o username exato que o usuário digitou
    const tokens = await fetchTokens(username, password);
    if (!tokens) {
      msgEl.innerHTML = '<div class="msg msg-error">Conta criada! Faça login para continuar.</div>';
      switchAuthTab('login');
      return;
    }

    tk.set(tokens.access, tokens.refresh);
    const me = await loadAndStoreUser();
    await claimAnonOccurrences();

    closeModal('modal-auth');
    toast('Conta criada com sucesso! Bem-vindo ao InfraMind.', 'success');
    updateNavbar(me);
  } catch (err) {
    console.error(err);
    msgEl.innerHTML = '<div class="msg msg-error">Erro de conexão com o servidor.</div>';
  }
}

// ══════════════════════════════════════════
// ATUALIZA NAVBAR APÓS LOGIN / CADASTRO
// Recebe o objeto user diretamente para não
// depender de leitura assíncrona do storage.
// ══════════════════════════════════════════
function updateNavbar(user) {
  const u = user || tk.user();
  const actionsEl = document.querySelector('.navbar-actions');
  if (!actionsEl) return;

  if (u && tk.get()) {
    const name = [u.first_name, u.last_name].filter(Boolean).join(' ') || u.username;
    actionsEl.innerHTML = `
      <span style="font-size:.82rem;color:#8b949e;white-space:nowrap">
        Olá, <strong style="color:#e6edf3">${name}</strong>
      </span>
      <a href="index.html" class="btn btn-primary">
        Ir para o sistema
      </a>`;
  } else {
    actionsEl.innerHTML = `
      <button class="btn btn-ghost" onclick="openAuthModal('login')">Fazer Login</button>
      <button class="btn btn-success" onclick="openOccModal()">
        <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
        Registrar Ocorrência
      </button>`;
  }
}

// ══════════════════════════════════════════
// OCCURRENCE MODAL
// ══════════════════════════════════════════
async function openOccModal() {
  const banner = document.getElementById('occ-anon-info');
  if (banner) banner.style.display = tk.get() ? 'none' : 'flex';
  document.getElementById('occ-msg').innerHTML = '';
  document.getElementById('occ-title').value = '';
  document.getElementById('occ-desc').value = '';
  removePhoto();
  const extras = document.getElementById('occ-extras');
  if (extras) extras.removeAttribute('open');
  resetLocWidget();
  openModal('modal-occ');
  await loadCategoriesForOcc();
}

async function loadCategoriesForOcc() {
  const sel = document.getElementById('occ-cat');
  try {
    const r = await apiFetch('/api/v1/categories/');
    const d = await r.json();
    const cats = Array.isArray(d) ? d : (d.results || []);
    sel.innerHTML = '<option value="">Selecione uma categoria</option>';
    cats.forEach(c => {
      const o = document.createElement('option');
      o.value = c.id; o.textContent = c.name;
      sel.appendChild(o);
    });
  } catch {
    sel.innerHTML = '<option value="">Erro ao carregar categorias</option>';
  }
}

function handlePhotoSelect(input) {
  const file = input.files[0];
  if (!file) return;
  if (file.size > 10 * 1024 * 1024) { alert('A foto deve ter no máximo 10 MB.'); input.value = ''; return; }
  const reader = new FileReader();
  reader.onload = (e) => {
    document.getElementById('occ-photo-thumb').src = e.target.result;
    document.getElementById('occ-photo-name').textContent = file.name;
    document.getElementById('occ-photo-drop').style.display = 'none';
    document.getElementById('occ-photo-preview').style.display = 'flex';
  };
  reader.readAsDataURL(file);
}

function removePhoto() {
  const input = document.getElementById('occ-photo-input');
  if (input) input.value = '';
  const thumb = document.getElementById('occ-photo-thumb');
  if (thumb) thumb.src = '';
  const drop = document.getElementById('occ-photo-drop');
  if (drop) drop.style.display = 'flex';
  const preview = document.getElementById('occ-photo-preview');
  if (preview) preview.style.display = 'none';
}

async function uploadOccPhoto(occId) {
  const input = document.getElementById('occ-photo-input');
  if (!input || !input.files[0]) return;
  const formData = new FormData();
  formData.append('occurrence', occId);
  formData.append('image_file', input.files[0]);
  try {
    if (tk.get()) {
      await apiFetch('/api/v1/images/', { method: 'POST', body: formData, headers: {} });
    } else {
      await fetch(`${API}/api/v1/images/anonymous/`, { method: 'POST', body: formData });
    }
  } catch (err) { console.warn('Foto não enviada:', err); }
}

async function submitOcc() {
  const cat   = document.getElementById('occ-cat').value;
  const msgEl = document.getElementById('occ-msg');
  msgEl.innerHTML = '';

  const locTab = document.querySelector('.loc-tab.active')?.dataset.tab || 'text';
  const addr   = (locTab === 'text')
                   ? (document.getElementById('occ-addr')?.value.trim() || '')
                   : (document.getElementById(`loc-${locTab}-display`)?.textContent.trim() || '');
  const lat    = document.getElementById('occ-lat').value || null;
  const lng    = document.getElementById('occ-lng').value || null;

  if (!cat && !addr && !lat) {
    msgEl.innerHTML = '<div class="msg msg-error">Informe ao menos a categoria ou a localização do problema.</div>';
    return;
  }

  const titleRaw = document.getElementById('occ-title').value.trim();
  const desc     = document.getElementById('occ-desc').value.trim();
  const catLabel = document.getElementById('occ-cat').selectedOptions[0]?.text || '';
  const title    = titleRaw ||
                   (catLabel && catLabel !== 'Carregando categorias...' && catLabel !== 'Selecione uma categoria'
                     ? `${catLabel}${addr ? ' — ' + addr : ''}`
                     : addr || 'Ocorrência registrada pela landing page');

  const occPayload = {
    title, description: desc || '', status: 'open',
    category: cat || null, address: addr || null,
    latitude:  lat ? parseFloat(parseFloat(lat).toFixed(5)) : null,
    longitude: lng ? parseFloat(parseFloat(lng).toFixed(5)) : null,
  };

  if (tk.get()) {
    msgEl.innerHTML = '<div class="msg msg-info">Registrando...</div>';
    try {
      const r = await apiFetch('/api/v1/occurrences/', { method: 'POST', body: JSON.stringify(occPayload) });
      const d = await r.json();
      if (!r.ok) { msgEl.innerHTML = `<div class="msg msg-error">Erro: ${JSON.stringify(d)}</div>`; return; }
      await uploadOccPhoto(d.id);
      closeModal('modal-occ');
      toast('Ocorrência registrada com sucesso!', 'success');
    } catch { msgEl.innerHTML = '<div class="msg msg-error">Erro de conexão.</div>'; }
    return;
  }

  msgEl.innerHTML = '<div class="msg msg-info">Registrando...</div>';
  try {
    const anonPayload = { ...occPayload, anon_id: getAnonId() };
    const r = await fetch(`${API}/api/v1/occurrences/anonymous/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(anonPayload),
    });
    const d = await r.json();
    if (!r.ok) { msgEl.innerHTML = `<div class="msg msg-error">Erro ao registrar: ${d.error || JSON.stringify(d)}</div>`; return; }
    saveAnonOcc({ id: d.id, anon_id: d.anon_id, title: occPayload.title });
    await uploadOccPhoto(d.id);
    closeModal('modal-occ');
    toast('Ocorrência registrada com sucesso!', 'success');
    setTimeout(() => {
      if (!tk.get()) {
        const wantRegister = confirm('✅ Ocorrência enviada!\n\nCrie uma conta para acompanhar a resolução.');
        if (wantRegister) openAuthModal('register');
      }
    }, 600);
  } catch { msgEl.innerHTML = '<div class="msg msg-error">Erro de conexão com o servidor.</div>'; }
}

// ══════════════════════════════════════════
// LOGIN PROMPT
// ══════════════════════════════════════════
function openLoginPrompt(action) {
  const titles = { validar: 'Faça login para validar', feedback: 'Faça login para enviar feedback' };
  const texts  = {
    validar:  'Para confirmar que este problema existe na sua região, você precisa ter uma conta no InfraMind.',
    feedback: 'Para avaliar a resolução desta ocorrência, você precisa estar logado.',
  };
  document.getElementById('login-prompt-title').textContent = titles[action] || 'Faça login para continuar';
  document.getElementById('login-prompt-text').textContent  = texts[action]  || 'Você precisa de uma conta para realizar esta ação.';
  openModal('modal-login-prompt');
}

// ══════════════════════════════════════════
// TOAST
// ══════════════════════════════════════════
function toast(msg, type = 'success') {
  const icons = {
    success: '<svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>',
    error:   '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>',
    info:    '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>',
  };
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.innerHTML = (icons[type] || '') + `<span>${msg}</span>`;
  document.getElementById('toast-root').appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ══════════════════════════════════════════
// NAVBAR SCROLL
// ══════════════════════════════════════════
window.addEventListener('scroll', () => {
  const nb = document.getElementById('navbar');
  if (nb) nb.style.background = window.scrollY > 40 ? 'rgba(13,17,23,.95)' : 'rgba(13,17,23,.85)';
});

// ══════════════════════════════════════════
// INIT
// ══════════════════════════════════════════
(function init() {
  // Atualiza navbar com sessão já existente
  updateNavbar();

  // Inicializa validação do campo username no cadastro
  initUsernameField('reg-username', 'reg-username-error');

  loadStats();

  const hash = window.location.hash;
  if (hash === '#login')    openAuthModal('login');
  if (hash === '#register') openAuthModal('register');
})();

// ══════════════════════════════════════════
// LOCATION WIDGET — GPS / MAP / TEXT
// ══════════════════════════════════════════
let _leafletMap = null;
let _leafletMarker = null;

function switchLocTab(tab, btn) {
  document.querySelectorAll('.loc-tab').forEach(b => {
    b.classList.remove('active');
    b.setAttribute('aria-selected', 'false');
  });
  btn.classList.add('active');
  btn.setAttribute('aria-selected', 'true');
  btn.dataset.tab = tab;
  document.querySelectorAll('.loc-pane').forEach(p => p.classList.remove('active'));
  document.getElementById('loc-pane-' + tab).classList.add('active');
  if (tab === 'map') initLeafletMap();
}

function resetLocWidget() {
  const tabs = document.querySelectorAll('.loc-tab');
  const tabNames = ['gps', 'map', 'text'];
  tabs.forEach((b, i) => {
    b.classList.toggle('active', i === 0);
    b.setAttribute('aria-selected', i === 0 ? 'true' : 'false');
    b.dataset.tab = tabNames[i];
  });
  document.querySelectorAll('.loc-pane').forEach((p, i) => p.classList.toggle('active', i === 0));
  const gpsRes = document.getElementById('gps-result');
  if (gpsRes) { gpsRes.style.display = 'none'; gpsRes.innerHTML = ''; }
  const gpsBtn = document.getElementById('gps-btn');
  if (gpsBtn) { gpsBtn.disabled = false; gpsBtn.classList.remove('loading', 'success'); }
  const lbl = document.getElementById('gps-btn-label');
  if (lbl) lbl.textContent = 'Usar minha localização atual';
  const addrEl = document.getElementById('occ-addr');
  if (addrEl) addrEl.value = '';
  const mapRes = document.getElementById('map-result');
  if (mapRes) { mapRes.style.display = 'none'; mapRes.innerHTML = ''; }
  if (_leafletMarker) { _leafletMarker.remove(); _leafletMarker = null; }
  document.getElementById('occ-lat').value = '';
  document.getElementById('occ-lng').value = '';
}

function requestGPS() {
  const btn   = document.getElementById('gps-btn');
  const label = document.getElementById('gps-btn-label');
  const res   = document.getElementById('gps-result');
  if (!navigator.geolocation) {
    res.innerHTML = '<span class="loc-err">Geolocalização não suportada neste navegador.</span>';
    res.style.display = 'flex'; return;
  }
  btn.disabled = true; btn.classList.add('loading');
  label.textContent = 'Obtendo localização…';
  res.style.display = 'none';
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const lat = pos.coords.latitude.toFixed(5);
      const lng = pos.coords.longitude.toFixed(5);
      document.getElementById('occ-lat').value = lat;
      document.getElementById('occ-lng').value = lng;
      btn.classList.remove('loading'); btn.classList.add('success');
      label.textContent = 'Localização capturada ✓';
      let addrText = lat + ', ' + lng;
      try {
        const r = await fetch('https://nominatim.openstreetmap.org/reverse?lat=' + lat + '&lon=' + lng + '&format=json',
          { headers: { 'Accept-Language': 'pt-BR' } });
        const d = await r.json();
        if (d.display_name) addrText = d.display_name;
      } catch {}
      res.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg><span id="loc-gps-display">' + addrText + '</span>';
      res.style.display = 'flex'; btn.disabled = false;
    },
    (err) => {
      btn.disabled = false; btn.classList.remove('loading');
      label.textContent = 'Usar minha localização atual';
      const msgs = { 1: 'Permissão negada.', 2: 'Localização indisponível.', 3: 'Tempo esgotado.' };
      res.innerHTML = '<span class="loc-err">' + (msgs[err.code] || 'Erro ao obter localização.') + '</span>';
      res.style.display = 'flex';
    },
    { timeout: 10000, maximumAge: 60000 }
  );
}

function initLeafletMap() {
  if (_leafletMap) { setTimeout(() => _leafletMap.invalidateSize(), 50); return; }
  if (!document.getElementById('leaflet-css')) {
    const link = document.createElement('link');
    link.id = 'leaflet-css'; link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
    document.head.appendChild(link);
  }
  if (!window.L) {
    const s = document.createElement('script');
    s.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    s.onload = () => _buildMap();
    document.head.appendChild(s);
  } else { _buildMap(); }
}

function _buildMap() {
  const el = document.getElementById('occ-map');
  if (!el || _leafletMap) return;
  _leafletMap = L.map('occ-map', { zoomControl: true }).setView([-22.4101, -47.5601], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>', maxZoom: 19,
  }).addTo(_leafletMap);
  _leafletMap.on('click', async (e) => {
    const { lat, lng } = e.latlng;
    document.getElementById('occ-lat').value = lat.toFixed(5);
    document.getElementById('occ-lng').value = lng.toFixed(5);
    if (_leafletMarker) { _leafletMarker.setLatLng(e.latlng); }
    else {
      _leafletMarker = L.marker(e.latlng, {
        icon: L.divIcon({ className: 'loc-map-marker', html: '<div class="loc-map-pin"></div>', iconSize: [28, 28], iconAnchor: [14, 28] }),
      }).addTo(_leafletMap);
    }
    const mapRes = document.getElementById('map-result');
    mapRes.innerHTML = '<span style="color:var(--muted);font-size:.8rem">Obtendo endereço…</span>';
    mapRes.style.display = 'flex';
    let addrText = lat.toFixed(5) + ', ' + lng.toFixed(5);
    try {
      const r = await fetch('https://nominatim.openstreetmap.org/reverse?lat=' + lat + '&lon=' + lng + '&format=json',
        { headers: { 'Accept-Language': 'pt-BR' } });
      const d = await r.json();
      if (d.display_name) addrText = d.display_name;
    } catch {}
    mapRes.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg><span id="loc-map-display">' + addrText + '</span>';
  });
  setTimeout(() => _leafletMap.invalidateSize(), 100);
}
