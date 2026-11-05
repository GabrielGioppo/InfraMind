/**
 * ══════════════════════════════════════════════════════════
 * InfraMind — Módulo de Recuperação de Senha (Esqueci Minha Senha)
 * Integrado em landing.html, index.html, admin.html e como-funciona.html
 * ══════════════════════════════════════════════════════════
 */

(function () {
  const getApiUrl = () => (typeof API !== 'undefined' ? API : 'http://127.0.0.1:8000');

  window.openForgotModal = function () {
    const modal = document.getElementById('forgot-modal');
    if (!modal) return;

    // Se houver outro modal de login aberto (como no index.html ou landing.html), podemos fechá-lo ou mantê-lo
    const authModal = document.getElementById('modal-auth');
    if (authModal && authModal.classList.contains('open')) {
      authModal.classList.remove('open');
    }

    const emailInp = document.getElementById('forgot-email');
    const msgEl = document.getElementById('forgot-msg');
    if (msgEl) {
      msgEl.className = 'forgot-msg';
      msgEl.innerHTML = '';
      msgEl.style.display = 'none';
    }

    // Tenta pré-preencher com o e-mail digitado no login, se houver
    const loginEmailInput = document.getElementById('auth-username') || document.getElementById('login-email') || document.getElementById('email');
    if (emailInp && loginEmailInput && loginEmailInput.value && loginEmailInput.value.includes('@')) {
      emailInp.value = loginEmailInput.value.trim();
    }

    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');

    if (emailInp) {
      setTimeout(() => emailInp.focus(), 100);
    }
  };

  window.closeForgotModal = function () {
    const modal = document.getElementById('forgot-modal');
    if (!modal) return;
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
  };

  window.submitForgotPassword = async function (e) {
    if (e && e.preventDefault) e.preventDefault();

    const emailInp = document.getElementById('forgot-email');
    const msgEl = document.getElementById('forgot-msg');
    const btn = document.getElementById('btn-forgot-submit');
    if (!emailInp) return;

    const email = emailInp.value.trim();
    if (!email) {
      if (msgEl) {
        msgEl.className = 'forgot-msg error';
        msgEl.textContent = 'Por favor, digite seu e-mail cadastrado.';
        msgEl.style.display = 'block';
      }
      return;
    }

    const resetPageUrl = new URL('redefinir-senha.html', window.location.href).href;

    if (btn) {
      btn.disabled = true;
      btn.dataset.prevHtml = btn.innerHTML;
      btn.innerHTML = `
        <svg viewBox="0 0 24 24" style="width:16px;height:16px;fill:currentColor;animation:spin 1s linear infinite;"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>
        Enviando...`;
    }

    if (msgEl) {
      msgEl.className = 'forgot-msg';
      msgEl.innerHTML = '';
      msgEl.style.display = 'none';
    }

    try {
      const res = await fetch(`${getApiUrl()}/authentication/password-reset/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, frontend_url: resetPageUrl })
      });

      const data = await res.json();

      if (res.ok) {
        if (msgEl) {
          msgEl.className = 'forgot-msg success';
          let html = `<div>${data.message || 'Se o e-mail estiver cadastrado, enviaremos um link para redefinir a senha.'}</div>`;
          if (data.dev_reset_link) {
            html += `
              <div style="margin-top:10px;padding-top:8px;border-top:1px dashed rgba(63,185,80,0.3);">
                <p style="font-size:0.78rem;margin:0 0 6px;color:#8b949e;">[Ambiente de Desenvolvimento] Link gerado:</p>
                <a href="${data.dev_reset_link}" style="display:inline-block;padding:6px 12px;background:#238636;color:white;text-decoration:none;border-radius:6px;font-size:0.8rem;font-weight:600;">
                  Redefinir Senha Agora &rarr;
                </a>
              </div>`;
          }
          msgEl.innerHTML = html;
          msgEl.style.display = 'block';
        }
        emailInp.value = '';
      } else {
        if (msgEl) {
          msgEl.className = 'forgot-msg error';
          msgEl.textContent = data.error || 'Não foi possível solicitar a redefinição de senha.';
          msgEl.style.display = 'block';
        }
      }
    } catch (err) {
      console.error('Erro ao solicitar redefinição de senha:', err);
      if (msgEl) {
        msgEl.className = 'forgot-msg error';
        msgEl.textContent = 'Erro ao conectar ao servidor. Verifique sua conexão e tente novamente.';
        msgEl.style.display = 'block';
      }
    } finally {
      if (btn) {
        btn.disabled = false;
        if (btn.dataset.prevHtml) btn.innerHTML = btn.dataset.prevHtml;
      }
    }
  };

  // Listeners globais de fechamento
  document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('forgot-modal');
    if (!modal) return;

    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeForgotModal();
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal.classList.contains('open')) {
        closeForgotModal();
      }
    });
  });
})();

