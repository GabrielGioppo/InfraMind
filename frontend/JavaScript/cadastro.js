// ═══════════════════════════════════════════════
// CADASTRO — CPF e endereço (usado por index.html e landing.html)
// Os campos têm os ids reg-cpf, reg-cep, reg-logradouro, reg-numero,
// reg-complemento, reg-bairro, reg-cidade e reg-uf.
// ═══════════════════════════════════════════════

const UFS = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'];

function soDigitos(v) { return String(v || '').replace(/\D/g, ''); }

// Mesma regra do backend (users/validators.py): 11 dígitos, não repetido e dígitos verificadores corretos.
function cpfValido(valor) {
  const cpf = soDigitos(valor);
  if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) return false;
  for (const tam of [9, 10]) {
    let soma = 0;
    for (let i = 0; i < tam; i++) soma += Number(cpf[i]) * (tam + 1 - i);
    if (((soma * 10) % 11) % 10 !== Number(cpf[tam])) return false;
  }
  return true;
}

function mascaraCpf(el) {
  const d = soDigitos(el.value).slice(0, 11);
  el.value = d.replace(/^(\d{3})(\d)/, '$1.$2').replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3').replace(/\.(\d{3})(\d)/, '.$1-$2');
}

function mascaraCep(el) {
  const d = soDigitos(el.value).slice(0, 8);
  el.value = d.length > 5 ? d.slice(0, 5) + '-' + d.slice(5) : d;
  if (d.length === 8) buscarCep();
}

// Preenche rua, bairro, cidade e UF pelo CEP (ViaCEP). Se falhar, o cidadão digita à mão.
let _ultimoCepBuscado = '';
async function buscarCep() {
  const cep = soDigitos(document.getElementById('reg-cep').value);
  if (cep.length !== 8 || cep === _ultimoCepBuscado) return;
  _ultimoCepBuscado = cep;
  try {
    const r = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
    const d = await r.json();
    if (d.erro) return;
    const set = (id, v) => { const el = document.getElementById(id); if (el && v) el.value = v; };
    set('reg-logradouro', d.logradouro);
    set('reg-bairro', d.bairro);
    set('reg-cidade', d.localidade);
    set('reg-uf', d.uf);
  } catch { /* sem internet ou ViaCEP fora do ar: preenchimento manual */ }
}

// Lê e valida os campos novos. Devolve { dados } ou { erro }.
function lerDadosCadastro() {
  const val = id => document.getElementById(id).value.trim();
  const dados = {
    cpf: val('reg-cpf'), cep: val('reg-cep'), logradouro: val('reg-logradouro'),
    numero: val('reg-numero'), complemento: val('reg-complemento'),
    bairro: val('reg-bairro'), cidade: val('reg-cidade'), uf: val('reg-uf').toUpperCase(),
  };
  if (!dados.cpf || !dados.cep || !dados.numero || !dados.bairro || !dados.cidade || !dados.uf)
    return { erro: 'Preencha CPF, CEP, número, bairro, cidade e UF.' };
  if (!cpfValido(dados.cpf)) return { erro: 'CPF inválido.' };
  if (soDigitos(dados.cep).length !== 8) return { erro: 'O CEP deve ter 8 dígitos.' };
  if (!UFS.includes(dados.uf)) return { erro: 'UF inválida. Use a sigla, ex.: SP.' };
  return { dados };
}

// Primeira mensagem de erro de uma resposta do DRF ({campo: ["msg"]} ou {error: "msg"}).
function mensagemDeErro(d) {
  if (!d || typeof d !== 'object') return 'Erro inesperado.';
  if (typeof d.error === 'string') return d.error;
  for (const [campo, msgs] of Object.entries(d)) {
    const m = Array.isArray(msgs) ? msgs[0] : msgs;
    if (typeof m === 'string') return (campo === 'non_field_errors' || campo === 'detail') ? m : `${campo}: ${m}`;
  }
  return 'Erro inesperado.';
}

// Bloco HTML dos campos novos (as duas telas de cadastro usam o mesmo).
const CAMPOS_CADASTRO_HTML = `
  <div class="field">
    <label>CPF</label>
    <input type="text" id="reg-cpf" placeholder="000.000.000-00" inputmode="numeric" autocomplete="off" oninput="mascaraCpf(this)">
  </div>
  <div class="field">
    <label>CEP</label>
    <input type="text" id="reg-cep" placeholder="00000-000" inputmode="numeric" autocomplete="postal-code" oninput="mascaraCep(this)" onblur="buscarCep()">
    <p class="field-hint">Preenchemos rua, bairro e cidade pelo CEP.</p>
  </div>
  <div class="field">
    <label>Rua / Logradouro</label>
    <input type="text" id="reg-logradouro" placeholder="Rua das Flores" autocomplete="address-line1">
  </div>
  <div class="field-row field-row-2">
    <div class="field">
      <label>Número</label>
      <input type="text" id="reg-numero" placeholder="120" autocomplete="off">
    </div>
    <div class="field">
      <label>Complemento <span class="opt">(opcional)</span></label>
      <input type="text" id="reg-complemento" placeholder="Ap 32" autocomplete="off">
    </div>
  </div>
  <div class="field">
    <label>Bairro</label>
    <input type="text" id="reg-bairro" placeholder="Centro" autocomplete="off">
  </div>
  <div class="field-row field-row-city">
    <div class="field">
      <label>Cidade</label>
      <input type="text" id="reg-cidade" placeholder="Sorocaba" autocomplete="address-level2">
    </div>
    <div class="field">
      <label>UF</label>
      <input type="text" id="reg-uf" placeholder="SP" maxlength="2" autocomplete="address-level1" style="text-transform:uppercase">
    </div>
  </div>
  <p class="field-hint" style="margin:-6px 0 16px">Você verá as ocorrências da cidade onde mora.</p>`;

document.querySelectorAll('[data-campos-cadastro]').forEach(el => { el.innerHTML = CAMPOS_CADASTRO_HTML; });
