'use strict';

function criarControleTranscricao(container, endpoint) {
  const descricao = document.getElementById(container.dataset.transcricao);
  const gravar = container.querySelector('[data-gravar]');
  const arquivo = container.querySelector('[type=file]');
  const status = container.querySelector('[role=status]');
  const cancelar = document.createElement('button');
  cancelar.type = 'button';
  cancelar.className = 'btn btn-ghost';
  cancelar.textContent = 'Cancelar áudio';
  cancelar.hidden = true;
  status.before(cancelar);

  const andamento = document.createElement('div');
  andamento.className = 'transcricao-andamento';
  andamento.hidden = true;
  andamento.innerHTML = `
    <div class="transcricao-cabecalho">
      <span class="transcricao-ondas" aria-hidden="true">
        <i></i><i></i><i></i><i></i><i></i>
      </span>
      <div class="transcricao-mensagem">
        <strong>Transcrevendo seu áudio</strong>
        <span>Aguarde enquanto transformamos a fala em texto.</span>
      </div>
      <span class="transcricao-tempo" aria-hidden="true">00:00</span>
    </div>
    <div class="transcricao-barra" role="progressbar" aria-label="Transcrição em andamento">
      <span></span>
    </div>
  `;
  cancelar.before(andamento);
  const tempo = andamento.querySelector('.transcricao-tempo');
  let cronometro = null;

  function mostrarAndamento(ativo) {
    clearInterval(cronometro);
    cronometro = null;
    andamento.hidden = !ativo;
    if (ativo) {
      const inicio = performance.now();
      tempo.textContent = '00:00';
      cronometro = setInterval(() => {
        const segundos = Math.floor((performance.now() - inicio) / 1000);
        tempo.textContent = `${String(Math.floor(segundos / 60)).padStart(2, '0')}:${String(segundos % 60).padStart(2, '0')}`;
      }, 1000);
    }
  }

  let gravador = null;
  let stream = null;
  let pedido = null;
  let limite = null;
  let sessao = 0;

  function ocupado(valor) {
    container.setAttribute('aria-busy', String(valor));
    gravar.disabled = valor;
    arquivo.disabled = valor;
    cancelar.hidden = !valor;
    cancelar.style.display = valor ? '' : 'none';
  }

  function pararMicrofone() {
    clearTimeout(limite);
    stream?.getTracks().forEach(track => track.stop());
    stream = null;
  }

  function resetar() {
    sessao++;
    pedido?.abort();
    pedido = null;
    if (gravador?.state === 'recording') gravador.stop();
    gravador = null;
    pararMicrofone();
    arquivo.value = '';
    gravar.textContent = 'Gravar áudio';
    status.textContent = '';
    mostrarAndamento(false);
    ocupado(false);
  }

  cancelar.addEventListener('click', resetar);
  window.addEventListener('pagehide', resetar);

  async function transcrever(audio) {
    if (!audio.size || audio.size > 10 * 1024 * 1024) {
      status.textContent = 'Escolha um áudio de até 10 MB e 60 segundos.';
      return;
    }
    const atual = sessao;
    const controller = new AbortController();
    pedido = controller;
    ocupado(true);
    mostrarAndamento(true);
    status.textContent = 'O texto aparecerá na descrição quando estiver pronto.';
    const timeout = setTimeout(() => controller.abort(), 180000);
    const dados = new FormData();
    dados.append('audio', audio);

    try {
      // Endpoint público: não envia cookies nem tokens de uma sessão antiga.
      const resposta = await fetch(endpoint, {
        method: 'POST', body: dados, signal: controller.signal, credentials: 'omit',
      });
      const resultado = await resposta.json();
      if (atual !== sessao) return;
      if (!resposta.ok || typeof resultado.transcript !== 'string' || !resultado.transcript.trim()) {
        status.textContent = resultado.detail || 'Não foi possível transcrever o áudio.';
        return;
      }
      descricao.value = [descricao.value.trim(), resultado.transcript.trim()].filter(Boolean).join('\n\n');
      descricao.dispatchEvent(new Event('input', { bubbles: true }));
      descricao.focus();
      status.textContent = 'Texto adicionado. Revise a descrição antes de enviar.';
    } catch (erro) {
      if (atual !== sessao) return;
      status.textContent = erro.name === 'AbortError'
        ? 'A transcrição demorou demais. Tente um áudio mais curto ou digite a descrição.'
        : 'Não foi possível transcrever. Confira a conexão e tente novamente.';
    } finally {
      clearTimeout(timeout);
      if (atual === sessao) {
        pedido = null;
        mostrarAndamento(false);
        ocupado(false);
      }
    }
  }

  arquivo.addEventListener('change', () => {
    const audio = arquivo.files[0];
    arquivo.value = '';
    if (audio) transcrever(audio);
  });

  gravar.addEventListener('click', async () => {
    if (gravador?.state === 'recording') {
      gravar.disabled = true;
      gravador.stop();
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      status.textContent = 'Microfone indisponível. Use localhost ou HTTPS, ou anexe um áudio.';
      return;
    }
    const atual = sessao;
    ocupado(true);
    status.textContent = 'Aguardando permissão do microfone…';
    try {
      const microfone = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      if (atual !== sessao) {
        microfone.getTracks().forEach(track => track.stop());
        return;
      }
      stream = microfone;
      const partes = [];
      const mimeType = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4']
        .find(tipo => MediaRecorder.isTypeSupported(tipo));
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
      gravador = recorder;
      recorder.ondataavailable = evento => { if (evento.data.size) partes.push(evento.data); };
      recorder.onstop = () => {
        if (atual !== sessao) return;
        pararMicrofone();
        gravador = null;
        gravar.textContent = 'Gravar áudio';
        ocupado(false);
        const tipo = recorder.mimeType.split(';')[0];
        const extensao = tipo.includes('ogg') ? 'ogg' : tipo.includes('mp4') ? 'm4a' : 'webm';
        transcrever(new File(partes, `gravacao.${extensao}`, { type: tipo }));
      };
      recorder.onerror = () => {
        if (atual !== sessao) return;
        resetar();
        status.textContent = 'A gravação falhou. Tente novamente ou anexe um arquivo.';
      };
      recorder.start();
      limite = setTimeout(() => {
        if (recorder.state === 'recording') {
          gravar.disabled = true;
          recorder.stop();
        }
      }, 59000);
      gravar.disabled = false;
      gravar.textContent = 'Parar e transcrever';
      status.textContent = 'Gravando… até 60 segundos.';
    } catch {
      if (atual !== sessao) return;
      resetar();
      status.textContent = 'Não consegui acessar o microfone. Verifique a permissão ou anexe um áudio.';
    }
  });
  ocupado(false);
  return resetar;
}
