// ═══════════════════════════════════════════════
// COMO FUNCIONA — InfraMind  |  como-funciona.js
// ═══════════════════════════════════════════════

const API = 'http://127.0.0.1:9000';

// ── Token helpers ──────────────────────────────
const tk = {
  get:     () => localStorage.getItem('im_access'),
  getRef:  () => localStorage.getItem('im_refresh'),
  set:     (a, r) => { localStorage.setItem('im_access', a); if (r) localStorage.setItem('im_refresh', r); },
  clear:   () => ['im_access','im_refresh','im_user'].forEach(k => localStorage.removeItem(k)),
  user:    () => { try { return JSON.parse(localStorage.getItem('im_user')); } catch { return null; } },
  setUser: (u) => localStorage.setItem('im_user', JSON.stringify(u)),
};

// ── API fetch ──────────────────────────────────
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

// ── Modal ──────────────────────────────────────
function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

document.querySelectorAll('.modal-overlay').forEach(o => {
  o.addEventListener('click', e => { if (e.target === o) o.classList.remove('open'); });
});

// ── Auth modal ─────────────────────────────────
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

// ── Password toggle ────────────────────────────
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

// ── Login ──────────────────────────────────────
async function doLogin() {
  const username = document.getElementById('login-username')?.value.trim() || '';
  const password = document.getElementById('login-password')?.value || '';
  const msgEl = document.getElementById('login-msg');
  msgEl.innerHTML = '';

  if (!username || !password) {
    msgEl.innerHTML = '<div class="msg msg-error">Preencha usuário e senha.</div>';
    return;
  }
  try {
    msgEl.innerHTML = '<div class="msg msg-info">Autenticando...</div>';
    const r = await fetch(`${API}/authentication/token/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const d = await r.json();
    if (!r.ok) {
      msgEl.innerHTML = '<div class="msg msg-error">Credenciais inválidas. Verifique e tente novamente.</div>';
      return;
    }
    tk.set(d.access, d.refresh);
    await loadAndStoreUser();
    closeModal('modal-auth');
    toast('Login realizado! Redirecionando...', 'success');
    updateNavbar();
    setTimeout(() => { window.location.href = 'index.html'; }, 900);
  } catch {
    msgEl.innerHTML = '<div class="msg msg-error">Erro de conexão com o servidor.</div>';
  }
}

// ── Register ───────────────────────────────────
async function doRegister() {
  const fullName = document.getElementById('reg-fullname')?.value.trim() || '';
  const email    = document.getElementById('reg-email')?.value.trim()    || '';
  const password = document.getElementById('reg-password')?.value        || '';
  const msgEl    = document.getElementById('register-msg');
  msgEl.innerHTML = '';

  if (!fullName || !email || !password) {
    msgEl.innerHTML = '<div class="msg msg-error">Preencha todos os campos.</div>'; return;
  }
  if (password.length < 8) {
    msgEl.innerHTML = '<div class="msg msg-error">A senha precisa ter pelo menos 8 caracteres.</div>'; return;
  }

  const parts    = fullName.split(' ');
  const username = fullName.toLowerCase().replace(/\s+/g,'_').replace(/[^a-z0-9_]/g,'')
                 + '_' + Math.floor(Math.random() * 900 + 100);
  const payload  = {
    username, email, password,
    first_name: parts[0],
    last_name: parts.slice(1).join(' '),
  };

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

    // Auto-login
    const lr = await fetch(`${API}/authentication/token/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: payload.username, password })
    });
    const ld = await lr.json();
    if (!lr.ok) { msgEl.innerHTML = '<div class="msg msg-success">Conta criada! Faça login para continuar.</div>'; switchTab('login'); return; }

    tk.set(ld.access, ld.refresh);
    await loadAndStoreUser();
    closeModal('modal-auth');
    toast('Conta criada com sucesso!', 'success');
    updateNavbar();
    setTimeout(() => { window.location.href = 'index.html'; }, 900);
  } catch {
    msgEl.innerHTML = '<div class="msg msg-error">Erro de conexão com o servidor.</div>';
  }
}

async function loadAndStoreUser() {
  try {
    const payload = JSON.parse(atob(tk.get().split('.')[1]));
    const r = await apiFetch('/api/v1/users/');
    const d = await r.json();
    const users = Array.isArray(d) ? d : (d.results || []);
    const me = users.find(u => u.id === payload.user_id);
    if (me) tk.setUser(me);
  } catch {}
}

// ── Update navbar for logged-in user ──────────
function updateNavbar() {
  const user = tk.user();
  const actionsEl = document.getElementById('navbar-actions');
  if (!actionsEl) return;

  if (user && tk.get()) {
    const name = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username;
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
      <button class="btn btn-success" onclick="window.location.href='landing.html#occ'">
        <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
        Registrar Ocorrência
      </button>`;
  }
}

// ── Active TOC link on scroll ──────────────────
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

// ── Navbar scroll effect ───────────────────────
window.addEventListener('scroll', () => {
  const nb = document.getElementById('top-navbar');
  if (!nb) return;
  nb.style.background = window.scrollY > 30
    ? 'rgba(13,17,23,.97)'
    : 'rgba(13,17,23,.9)';
}, { passive: true });

// ── Toast ──────────────────────────────────────
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

// ── Init ───────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  updateNavbar();
  initScrollSpy();

  // Keyboard: Enter to submit login
  document.getElementById('login-password')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') doLogin();
  });
  document.getElementById('reg-password')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') doRegister();
  });
});
