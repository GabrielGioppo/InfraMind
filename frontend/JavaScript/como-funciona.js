// ═══════════════════════════════════════════════
// COMO FUNCIONA — InfraMind
// ═══════════════════════════════════════════════

const API = 'http://127.0.0.1:9000';

const tk = {
  get:     () => localStorage.getItem('im_access'),
  getRef:  () => localStorage.getItem('im_refresh'),
  set:     (a, r) => { localStorage.setItem('im_access', a); if (r) localStorage.setItem('im_refresh', r); },
  clear:   () => ['im_access','im_refresh','im_user'].forEach(k => localStorage.removeItem(k)),
  user:    () => { try { return JSON.parse(localStorage.getItem('im_user')); } catch { return null; } },
  setUser: (u) => localStorage.setItem('im_user', JSON.stringify(u)),
};

async function apiFetch(path, opts = {}) {
  const hdrs = { ...opts.headers };
  if (tk.get()) hdrs['Authorization'] = `Bearer ${tk.get()}`;
  if (!(opts.body instanceof FormData)) hdrs['Content-Type'] = 'application/json';
  let res = await fetch(`${API}${path}`, { ...opts, headers: hdrs });
  if (res.status === 401 && tk.getRef()) {
    try {
      const r = await fetch(`${API}/authentication/token/refresh/`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: tk.getRef() })
      });
      if (r.ok) {
        const d = await r.json();
        tk.set(d.access);
        hdrs['Authorization'] = `Bearer ${tk.get()}`;
        res = await fetch(`${API}${path}`, { ...opts, headers: hdrs });
      } else { tk.clear(); }
    } catch {}
  }
  return res;
}

// ── Obtém tokens por username OU e-mail ────────
async function fetchTokens(usernameOrEmail, password) {
  const r1 = await fetch(`${API}/authentication/token/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: usernameOrEmail, password })
  });
  if (r1.ok) return await r1.json();

  const r2 = await fetch(`${API}/authentication/login/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: usernameOrEmail, password })
  });
  if (r2.ok) return await r2.json();

  return null;
}

// ── Salva o usuário logado (busca por ID) ──────
async function loadAndStoreUser() {
  try {
    const payload = JSON.parse(atob(tk.get().split('.')[1]));
    const userId  = payload.user_id;
    const r = await apiFetch(`/api/v1/users/${userId}/`);
    if (r.ok) {
      const me = await r.json();
      tk.setUser(me);
      return me;
    }
    // Fallback para admins
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

// ── Modal ──────────────────────────────────────
function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

document.querySelectorAll('.modal-overlay').forEach(o => {
  o.addEventListener('click', e => { if (e.target === o) o.classList.remove('open'); });
});

function openAuthModal(tab) {
  switchTab(tab);
  clearMsgs();
  openModal('modal-auth');
}

function switchTab(tab) {
  ['login','register'].forEach(t => {
    document.getElementById(`tab-${t}`)?.classList.toggle('active', t === tab);
    document.getElementById(`pane-${t}`)?.classList.toggle('active', t === tab);
  });
}

function clearMsgs() {
  ['login-msg','register-msg'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = '';
  });
}

function togglePw(id, btn) {
  const inp = document.getElementById(id);
  const isText = inp.type === 'text';
  inp.type = isText ? 'password' : 'text';
  const path = btn.querySelector('svg path');
  if (!path) return;
  path.setAttribute('d', isText
    ? 'M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z'
    : 'M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.82l2.92 2.92c1.51-1.26 2.7-2.89 3.44-4.74-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27z'
  );
}

// ── Validação do campo username ────────────────
function initUsernameField(inputId, errorId) {
  const input   = document.getElementById(inputId);
  const errorEl = document.getElementById(errorId);
  if (!input) return;

  input.addEventListener('keydown', e => {
    if (e.key === ' ') e.preventDefault();
  });

  input.addEventListener('input', () => {
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

// ── Login ──────────────────────────────────────
async function doLogin() {
  const usernameOrEmail = document.getElementById('login-username')?.value.trim() || '';
  const password = document.getElementById('login-password')?.value || '';
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
    closeModal('modal-auth');
    toast('Login realizado com sucesso!', 'success');
    updateNavbar(me);
  } catch (err) {
    console.error(err);
    msgEl.innerHTML = '<div class="msg msg-error">Erro de conexão com o servidor.</div>';
  }
}

// ── Register — auto-login, sem redirecionar ────
async function doRegister() {
  const username = document.getElementById('reg-username')?.value.trim() || '';
  const email    = document.getElementById('reg-email')?.value.trim()    || '';
  const password = document.getElementById('reg-password')?.value        || '';
  const msgEl    = document.getElementById('register-msg');
  msgEl.innerHTML = '';

  if (!username || !email || !password) {
    msgEl.innerHTML = '<div class="msg msg-error">Preencha todos os campos.</div>'; return;
  }
  if (!/^[a-zA-Z0-9_]+$/.test(username)) {
    msgEl.innerHTML = '<div class="msg msg-error">O usuário só pode conter letras, números e _. Sem espaços.</div>'; return;
  }
  if (password.length < 8) {
    msgEl.innerHTML = '<div class="msg msg-error">A senha precisa ter pelo menos 8 caracteres.</div>'; return;
  }

  const payload = { username, email, password };

  try {
    msgEl.innerHTML = '<div class="msg msg-info">Criando conta...</div>';
    const r = await fetch(`${API}/api/v1/users/register/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const d = await r.json();
    if (!r.ok) {
      msgEl.innerHTML = `<div class="msg msg-error">Erro: ${d.email?.[0] || d.username?.[0] || JSON.stringify(d)}</div>`; return;
    }

    const tokens = await fetchTokens(username, password);
    if (!tokens) {
      msgEl.innerHTML = '<div class="msg msg-success">Conta criada! Faça login para continuar.</div>';
      switchTab('login');
      return;
    }

    tk.set(tokens.access, tokens.refresh);
    const me = await loadAndStoreUser();
    closeModal('modal-auth');
    toast('Conta criada com sucesso!', 'success');
    updateNavbar(me);
  } catch (err) {
    console.error(err);
    msgEl.innerHTML = '<div class="msg msg-error">Erro de conexão com o servidor.</div>';
  }
}

// ── Atualiza navbar ────────────────────────────
function updateNavbar(user) {
  const u = user || tk.user();
  const actionsEl = document.getElementById('navbar-actions');
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
      <button class="btn btn-success" onclick="window.location.href='landing.html'">
        <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
        Registrar Ocorrência
      </button>`;
  }
}

// ── TOC scroll spy ─────────────────────────────
function initScrollSpy() {
  const sections = document.querySelectorAll('[data-section]');
  const links    = document.querySelectorAll('.toc-item a');
  if (!sections.length || !links.length) return;
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.dataset.section;
        links.forEach(l => l.classList.toggle('active', l.getAttribute('href') === `#${id}`));
      }
    });
  }, { rootMargin: '-30% 0px -60% 0px' });
  sections.forEach(s => observer.observe(s));
}

window.addEventListener('scroll', () => {
  const nb = document.getElementById('top-navbar');
  if (!nb) return;
  nb.style.background = window.scrollY > 30 ? 'rgba(13,17,23,.97)' : 'rgba(13,17,23,.9)';
}, { passive: true });

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
  setTimeout(() => el.remove(), 4200);
}

document.addEventListener('DOMContentLoaded', () => {
  updateNavbar();
  initScrollSpy();
  initUsernameField('reg-username', 'reg-username-error');

  document.getElementById('login-password')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') doLogin();
  });
  document.getElementById('reg-password')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') doRegister();
  });
});