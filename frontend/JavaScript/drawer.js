// ══════════════════════════════════════════════════════
// GAVETA DO USUÁRIO (USER DRAWER) — InfraMind
// ══════════════════════════════════════════════════════

function openUserDrawer() {
  const drawer = document.getElementById('user-drawer');
  const overlay = document.getElementById('user-drawer-overlay');
  if (drawer && overlay) {
    refreshDrawerUserData();
    drawer.classList.add('open');
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
}

function closeUserDrawer() {
  const drawer = document.getElementById('user-drawer');
  const overlay = document.getElementById('user-drawer-overlay');
  if (drawer && overlay) {
    drawer.classList.remove('open');
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  }
}

function toggleUserDrawer() {
  const drawer = document.getElementById('user-drawer');
  if (drawer && drawer.classList.contains('open')) {
    closeUserDrawer();
  } else {
    openUserDrawer();
  }
}

function refreshDrawerUserData() {
  let user = null;
  try {
    user = JSON.parse(localStorage.getItem('im_user'));
  } catch (e) {}

  const sessionName = localStorage.getItem('infraMind_session_name');
  const sessionEmail = localStorage.getItem('infraMind_session_email');

  let name = 'Usuário';
  let role = 'Cidadão';
  let isAdmin = false;
  let picture = null;

  if (user) {
    name = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username || 'Usuário';
    isAdmin = user.user_type === 'admin' || user.is_staff;
    role = isAdmin ? 'Administrador' : 'Cidadão';
    picture = user.profile_picture || null;
  } else if (sessionName) {
    name = sessionName;
    role = 'Administrador';
    isAdmin = true;
  }

  const nameEl = document.getElementById('drawer-user-name');
  if (nameEl) nameEl.textContent = name;

  const roleEl = document.getElementById('drawer-user-role');
  if (roleEl) {
    roleEl.innerHTML = `<span class="user-drawer-role-badge ${isAdmin ? 'admin' : ''}">${role}</span>`;
  }

  const avatarEl = document.getElementById('drawer-user-avatar');
  if (avatarEl) {
    if (picture) {
      const src = picture.startsWith('http') ? picture : `http://127.0.0.1:9000${picture}`;
      avatarEl.innerHTML = `<img src="${src}" alt="${name}" onerror="this.onerror=null;this.parentElement.textContent='${name.charAt(0).toUpperCase()}';">`;
    } else {
      avatarEl.textContent = name.charAt(0).toUpperCase();
    }
  }
}

// Fechar com tecla Escape
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeUserDrawer();
});
