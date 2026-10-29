// ══════════════════════════════════════════════════════
// PERFIL & DASHBOARD DO USUÁRIO — InfraMind
// ══════════════════════════════════════════════════════

const API = 'http://127.0.0.1:9000';

let CURRENT_USER = null;
let SELECTED_PHOTO_FILE = null;
let REMOVE_PHOTO_FLAG = false;

// ── Obtenção e controle de tokens ──────────────────────
function getAccessToken() {
  return localStorage.getItem('im_access') || localStorage.getItem('infraMind_access_token');
}

function getRefreshToken() {
  return localStorage.getItem('im_refresh') || localStorage.getItem('infraMind_refresh_token');
}

function setTokens(access, refresh) {
  if (access) {
    localStorage.setItem('im_access', access);
    localStorage.setItem('infraMind_access_token', access);
  }
  if (refresh) {
    localStorage.setItem('im_refresh', refresh);
    localStorage.setItem('infraMind_refresh_token', refresh);
  }
}

function doGlobalLogout() {
  [
    'im_access', 'im_refresh', 'im_user',
    'infraMind_access_token', 'infraMind_refresh_token',
    'infraMind_session_name', 'infraMind_session_email', 'infraMind_session_id'
  ].forEach(k => localStorage.removeItem(k));
  window.location.href = 'index.html';
}

// ── Wrapper para requisições autenticadas ──────────────
async function authFetch(path, options = {}) {
  const token = getAccessToken();
  const headers = { ...(options.headers || {}) };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Não seta Content-Type se for FormData (o browser define boundary automaticamente)
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  let res = await fetch(`${API}${path}`, { ...options, headers });

  if (res.status === 401) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${getAccessToken()}`;
      res = await fetch(`${API}${path}`, { ...options, headers });
    } else {
      doGlobalLogout();
      return res;
    }
  }

  return res;
}

async function tryRefreshToken() {
  const ref = getRefreshToken();
  if (!ref) return false;
  try {
    const res = await fetch(`${API}/authentication/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: ref }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    setTokens(data.access, null);
    return true;
  } catch {
    return false;
  }
}

// ── Notificações Toasts ────────────────────────────────
function showToast(msg, type = 'success') {
  const container = document.getElementById('profile-toasts');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const icon = type === 'success'
    ? `<svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>`
    : `<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>`;

  toast.innerHTML = `${icon}<span>${msg}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 250);
  }, 3800);
}

// ── Máscaras de Entrada (CPF e Telefone) ────────────────
function maskCPF(input) {
  let v = input.value.replace(/\D/g, '');
  if (v.length > 11) v = v.slice(0, 11);
  v = v.replace(/(\d{3})(\d)/, '$1.$2');
  v = v.replace(/(\d{3})(\d)/, '$1.$2');
  v = v.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
  input.value = v;
}

function maskPhone(input) {
  let v = input.value.replace(/\D/g, '');
  if (v.length > 11) v = v.slice(0, 11);
  if (v.length > 10) {
    // Celular com 9 dígitos: (11) 98888-8888
    v = v.replace(/^(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3');
  } else if (v.length > 6) {
    // Fixo ou em digitação: (11) 4444-4444
    v = v.replace(/^(\d{2})(\d{4})(\d{0,4})$/, '($1) $2-$3');
  } else if (v.length > 2) {
    v = v.replace(/^(\d{2})(\d{0,5})$/, '($1) $2');
  }
  input.value = v;
}

function togglePasswordVisibility(inputId, btn) {
  const inp = document.getElementById(inputId);
  if (!inp) return;
  const isPass = inp.type === 'password';
  inp.type = isPass ? 'text' : 'password';

  const path = btn.querySelector('svg path');
  if (path) {
    path.setAttribute('d', isPass
      ? 'M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.82l2.92 2.92c1.51-1.26 2.7-2.89 3.44-4.74-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27z'
      : 'M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z'
    );
  }
}

// ── Manipulação de Foto de Perfil ──────────────────────
function handlePhotoSelect(e) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;

  if (!file.type.startsWith('image/')) {
    showToast('Selecione um arquivo de imagem válido.', 'error');
    return;
  }

  if (file.size > 5 * 1024 * 1024) {
    showToast('A imagem deve ter no máximo 5MB.', 'error');
    return;
  }

  SELECTED_PHOTO_FILE = file;
  REMOVE_PHOTO_FLAG = false;

  // Preview local imediato
  const reader = new FileReader();
  reader.onload = ev => {
    renderAvatarImage(ev.target.result);
    const removeBtn = document.getElementById('btn-remove-photo');
    if (removeBtn) removeBtn.style.display = 'inline-block';
  };
  reader.readAsDataURL(file);
}

function removeProfilePhoto() {
  SELECTED_PHOTO_FILE = null;
  REMOVE_PHOTO_FLAG = true;
  document.getElementById('profile-photo-input').value = '';

  const initial = (CURRENT_USER?.username || 'U').charAt(0).toUpperCase();
  const avatarEl = document.getElementById('profile-avatar-display');
  if (avatarEl) {
    avatarEl.innerHTML = `<span id="profile-avatar-initials">${initial}</span>`;
  }
  const removeBtn = document.getElementById('btn-remove-photo');
  if (removeBtn) removeBtn.style.display = 'none';
}

function renderAvatarImage(url) {
  const avatarEl = document.getElementById('profile-avatar-display');
  if (!avatarEl) return;
  avatarEl.innerHTML = `<img src="${url}" alt="Foto de perfil" onerror="this.onerror=null;this.parentElement.textContent='${(CURRENT_USER?.username||'U').charAt(0).toUpperCase()}';">`;
}

// ── Carregar Dados do Usuário e Estatísticas ───────────
async function loadUserProfile() {
  const token = getAccessToken();
  if (!token) {
    window.location.href = 'index.html';
    return;
  }

  try {
    let userData = null;
    const res = await authFetch('/api/v1/users/me/');

    if (res.ok) {
      userData = await res.json();
    } else {
      // Fallback: busca via listagem
      const resList = await authFetch('/api/v1/users/');
      if (resList.ok) {
        const listData = await resList.json();
        const users = Array.isArray(listData) ? listData : (listData.results || []);
        let saved = null;
        try { saved = JSON.parse(localStorage.getItem('im_user')); } catch {}
        userData = users.find(u => u.username === saved?.username || u.email === saved?.email) || users[0];
      }
    }

    if (!userData) {
      showToast('Não foi possível carregar os dados do usuário.', 'error');
      return;
    }

    CURRENT_USER = userData;
    localStorage.setItem('im_user', JSON.stringify(userData));
    localStorage.setItem('infraMind_session_name', [userData.first_name, userData.last_name].filter(Boolean).join(' ') || userData.username);
    localStorage.setItem('infraMind_session_email', userData.email);

    renderUserDataToUI(userData);
    loadUserActivityStats(userData);
    refreshDrawerUserData();
  } catch (err) {
    console.error('Erro ao carregar perfil:', err);
    showToast('Erro de conexão ao carregar perfil.', 'error');
  }
}

function renderUserDataToUI(u) {
  const fullName = [u.first_name, u.last_name].filter(Boolean).join(' ') || u.username;
  const isAdmin = u.user_type === 'admin' || u.is_staff;

  // Header e Barra Superior
  document.getElementById('top-user-name').textContent = fullName;
  const topAvatar = document.getElementById('top-user-avatar');
  if (topAvatar) {
    if (u.profile_picture) {
      const src = u.profile_picture.startsWith('http') ? u.profile_picture : `${API}${u.profile_picture}`;
      topAvatar.innerHTML = `<img src="${src}" alt="${fullName}" style="width:100%;height:100%;object-fit:cover;">`;
    } else {
      topAvatar.textContent = fullName.charAt(0).toUpperCase();
    }
  }

  // Atualiza botão de voltar dependendo do perfil
  const backBtn = document.getElementById('btn-back-system');
  const drawerSystemLink = document.getElementById('drawer-system-link');
  if (isAdmin) {
    if (backBtn) { backBtn.href = 'admin.html'; document.getElementById('back-btn-text').textContent = 'Voltar ao Admin'; }
    if (drawerSystemLink) { drawerSystemLink.href = 'admin.html'; }
  } else {
    if (backBtn) { backBtn.href = 'index.html'; document.getElementById('back-btn-text').textContent = 'Voltar ao Sistema'; }
    if (drawerSystemLink) { drawerSystemLink.href = 'index.html'; }
  }

  // Card Lateral Esquerdo
  document.getElementById('side-user-fullname').textContent = fullName;
  document.getElementById('side-user-username').textContent = `@${u.username}`;
  
  const badgeEl = document.getElementById('side-user-badge');
  badgeEl.textContent = isAdmin ? 'Administrador' : 'Cidadão';
  badgeEl.className = `profile-badge ${isAdmin ? 'admin' : 'citizen'}`;

  // Avatar grande
  if (u.profile_picture) {
    const src = u.profile_picture.startsWith('http') ? u.profile_picture : `${API}${u.profile_picture}`;
    renderAvatarImage(src);
    document.getElementById('btn-remove-photo').style.display = 'inline-block';
  } else {
    document.getElementById('profile-avatar-display').innerHTML = `<span id="profile-avatar-initials">${fullName.charAt(0).toUpperCase()}</span>`;
    document.getElementById('btn-remove-photo').style.display = 'none';
  }

  // Preenchimento dos Campos do Formulário
  document.getElementById('f-username').value = u.username || '';
  document.getElementById('f-first-name').value = u.first_name || '';
  document.getElementById('f-last-name').value = u.last_name || '';
  document.getElementById('f-cpf').value = u.cpf || '';
  document.getElementById('f-phone').value = u.phone || '';
  document.getElementById('f-email').value = u.email || '';

  // Aplica máscaras aos valores iniciais
  maskCPF(document.getElementById('f-cpf'));
  maskPhone(document.getElementById('f-phone'));

  // Data de cadastro
  if (u.created_at) {
    const dt = new Date(u.created_at).toLocaleDateString('pt-BR');
    document.getElementById('side-user-meta').textContent = `Membro da plataforma InfraMind desde ${dt}.`;
  }
}

// ── Estatísticas de Atividade do Usuário ───────────────
async function loadUserActivityStats(user) {
  try {
    const [rOcc, rVal, rFeed] = await Promise.all([
      authFetch('/api/v1/occurrences/'),
      authFetch('/api/v1/validations/'),
      authFetch('/api/v1/feedbacks/'),
    ]);

    if (rOcc.ok) {
      const occData = await rOcc.json();
      const occList = Array.isArray(occData) ? occData : (occData.results || []);
      // Ocorrências criadas pelo próprio usuário
      const myOccs = occList.filter(o => o.user === user.username || o.user === user.id || o.user_id === user.id);
      document.getElementById('stat-user-occs').textContent = myOccs.length;
    }

    if (rVal.ok) {
      const valData = await rVal.json();
      const valList = Array.isArray(valData) ? valData : (valData.results || []);
      document.getElementById('stat-user-val').textContent = valList.length;
    }

    if (rFeed.ok) {
      const feedData = await rFeed.json();
      const feedList = Array.isArray(feedData) ? feedData : (feedData.results || []);
      const myFeeds = feedList.filter(f => f.user === user.username || f.user_id === user.id);
      document.getElementById('stat-user-feed').textContent = myFeeds.length;
    }
  } catch (e) {
    console.warn('Estatísticas de usuário indisponíveis no momento:', e);
  }
}

// ── Resetar formulário ────────────────────────────────
function resetFormToLoadedData() {
  if (CURRENT_USER) {
    SELECTED_PHOTO_FILE = null;
    REMOVE_PHOTO_FLAG = false;
    document.getElementById('f-new-password').value = '';
    document.getElementById('f-confirm-password').value = '';
    renderUserDataToUI(CURRENT_USER);
    showToast('Dados restaurados ao estado inicial.', 'success');
  }
}

// ── Salvar Perfil do Usuário ──────────────────────────
async function saveUserProfile(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-submit-profile');
  btn.disabled = true;
  btn.innerHTML = `
    <svg viewBox="0 0 24 24" style="width:16px;height:16px;fill:currentColor;animation:spin 1s linear infinite;"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>
    Salvando...`;

  const username  = document.getElementById('f-username').value.trim();
  const firstName = document.getElementById('f-first-name').value.trim();
  const lastName  = document.getElementById('f-last-name').value.trim();
  const cpf       = document.getElementById('f-cpf').value.trim();
  const phone     = document.getElementById('f-phone').value.trim();
  const email     = document.getElementById('f-email').value.trim();
  const newPass   = document.getElementById('f-new-password').value;
  const confPass  = document.getElementById('f-confirm-password').value;

  // Validação de username
  if (!username) {
    showToast('O nome de usuário não pode ficar vazio.', 'error');
    btn.disabled = false; btn.textContent = 'Salvar Alterações'; return;
  }
  if (!/^[a-zA-Z0-9_]+$/.test(username)) {
    showToast('O nome de usuário deve conter apenas letras, números e _.', 'error');
    btn.disabled = false; btn.textContent = 'Salvar Alterações'; return;
  }

  // Validação de senha
  if (newPass) {
    if (newPass.length < 8) {
      showToast('A nova senha deve ter pelo menos 8 caracteres.', 'error');
      btn.disabled = false; btn.textContent = 'Salvar Alterações'; return;
    }
    if (newPass !== confPass) {
      showToast('A confirmação da nova senha não confere.', 'error');
      btn.disabled = false; btn.textContent = 'Salvar Alterações'; return;
    }
  }

  // Montagem do payload em FormData para suportar arquivo de foto
  const formData = new FormData();
  formData.append('username', username);
  formData.append('first_name', firstName);
  formData.append('last_name', lastName);
  formData.append('cpf', cpf);
  formData.append('phone', phone);
  formData.append('email', email);

  if (newPass) {
    formData.append('password', newPass);
  }

  if (SELECTED_PHOTO_FILE) {
    formData.append('profile_picture', SELECTED_PHOTO_FILE);
  } else if (REMOVE_PHOTO_FLAG) {
    formData.append('profile_picture', '');
  }

  try {
    const res = await authFetch('/api/v1/users/me/', {
      method: 'PATCH',
      body: formData,
    });

    if (res.ok) {
      const updatedUser = await res.json();
      CURRENT_USER = updatedUser;
      localStorage.setItem('im_user', JSON.stringify(updatedUser));
      localStorage.setItem('infraMind_session_name', [updatedUser.first_name, updatedUser.last_name].filter(Boolean).join(' ') || updatedUser.username);
      localStorage.setItem('infraMind_session_email', updatedUser.email);

      // Limpa os campos de senha
      document.getElementById('f-new-password').value = '';
      document.getElementById('f-confirm-password').value = '';
      SELECTED_PHOTO_FILE = null;
      REMOVE_PHOTO_FLAG = false;

      renderUserDataToUI(updatedUser);
      refreshDrawerUserData();
      showToast('✓ Perfil atualizado com sucesso!', 'success');
    } else {
      const err = await res.json();
      const firstMsg = Object.values(err).flat()[0] || 'Erro ao atualizar perfil.';
      showToast(String(firstMsg), 'error');
    }
  } catch (error) {
    console.error('Erro ao salvar perfil:', error);
    showToast('Erro de conexão com o servidor.', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `
      <svg viewBox="0 0 24 24" style="width:16px;height:16px;fill:currentColor;"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
      Salvar Alterações`;
  }
}

// ── Inicialização ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadUserProfile();

  // Validação em tempo real do campo de username
  const userInput = document.getElementById('f-username');
  const userErr = document.getElementById('f-username-error');
  if (userInput && userErr) {
    userInput.addEventListener('input', () => {
      const clean = userInput.value.replace(/[^a-zA-Z0-9_]/g, '');
      if (userInput.value !== clean) userInput.value = clean;
      if (userInput.value.length > 0 && !/^[a-zA-Z0-9_]+$/.test(userInput.value)) {
        userErr.textContent = 'Apenas letras, números e _ são permitidos.';
        userErr.style.display = 'block';
      } else {
        userErr.style.display = 'none';
      }
    });
  }
});
