const analista = decodeURIComponent(location.pathname.split('/').filter(Boolean).pop() || '');
document.getElementById('analista-label').textContent = analista ? `Olá, ${analista}` : '';

let analises = [];
let notas = {};        // { decisao_id: nota }
let idx = 0;

function escapeHtml(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[c]);
}

async function carregar() {
  const [a, n] = await Promise.all([
    fetch('/estudo/analises').then(r => r.json()),
    fetch(`/avaliacoes/${encodeURIComponent(analista)}`).then(r => r.json()),
  ]);
  analises = a;
  notas = n;
  if (!analises.length) {
    document.getElementById('conteudo').innerHTML =
      '<p class="text-muted">Nenhuma análise disponível ainda. Volte mais tarde.</p>';
    document.getElementById('progresso').textContent = 'Avaliação';
    document.getElementById('btn-anterior').disabled = true;
    document.getElementById('btn-proxima').disabled = true;
    return;
  }
  const primeiraSemNota = analises.findIndex(x => !(String(x.decisao_id) in notas));
  idx = primeiraSemNota >= 0 ? primeiraSemNota : 0;
  render();
}

function render() {
  document.getElementById('msg').innerHTML = '';
  const item = analises[idx];
  const pt = item.parecer_tecnico || {};
  const ds = item.dados_solicitante || {};
  document.getElementById('progresso').textContent = `Análise ${idx + 1} de ${analises.length}`;
  const avaliadas = analises.filter(x => String(x.decisao_id) in notas).length;
  document.getElementById('contador').textContent = `${avaliadas}/${analises.length} avaliadas`;

  const notaAtual = notas[String(item.decisao_id)];
  const escala = Array.from({length: 11}, (_, i) =>
    `<button class="nota-btn ${notaAtual === i ? 'ativa' : ''}" data-nota="${i}">${i}</button>`
  ).join('');

  const similares = (item.casos_similares || []).map(c =>
    `<li class="small text-muted">Caso #${c.caso_id} · ${c.decisao_final} · score ${Number(c.score).toFixed(2)}</li>`
  ).join('');

  document.getElementById('conteudo').innerHTML = `
    <div class="card card-siach p-4">
      <div class="d-flex justify-content-between mb-2">
        <span class="recomendacao-${item.recomendacao}">Recomendação: ${String(item.recomendacao).replace(/_/g,' ')}</span>
        <span class="text-muted">Confiança: ${(item.confianca * 100).toFixed(0)}%</span>
      </div>
      <p class="text-muted small mb-2">
        ${escapeHtml(ds.atividade_principal || '')} ·
        R$ ${(ds.valor_solicitado || 0).toLocaleString('pt-BR')} ·
        ${ds.prazo_meses || '—'} meses · score ${ds.score_interno ?? '—'}
      </p>
      <div class="parecer-humanizado mb-3">${escapeHtml(item.parecer_humanizado)}</div>
      <details class="mb-3">
        <summary>Detalhes técnicos e casos similares</summary>
        <h6 class="mt-2">Fatores favoráveis</h6>
        <ul>${(pt.fatores_favoraveis||[]).map(f=>`<li>${escapeHtml(f)}</li>`).join('')}</ul>
        <h6>Fatores de risco</h6>
        <ul>${(pt.fatores_de_risco||[]).map(f=>`<li>${escapeHtml(f)}</li>`).join('')}</ul>
        <h6>Casos similares</h6>
        <ul>${similares || '<li class="small text-muted">—</li>'}</ul>
      </details>
      <label class="form-label fw-bold text-success">Sua nota para esta análise (0–10):</label>
      <div class="nota-row" id="nota-row">${escala}</div>
    </div>
  `;

  document.querySelectorAll('#nota-row .nota-btn').forEach(btn => {
    btn.addEventListener('click', () => salvarNota(item.decisao_id, parseInt(btn.dataset.nota, 10)));
  });

  document.getElementById('btn-anterior').disabled = idx === 0;
  document.getElementById('btn-proxima').disabled = idx >= analises.length - 1;
}

async function salvarNota(decisaoId, nota) {
  const msg = document.getElementById('msg');
  document.querySelectorAll('#nota-row .nota-btn').forEach(b => b.disabled = true);
  try {
    const r = await fetch('/avaliacoes', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ analista, decisao_id: decisaoId, nota }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    notas[String(decisaoId)] = nota;
    render();
    document.querySelectorAll('#nota-row .nota-btn').forEach(b => b.disabled = true);
    if (idx < analises.length - 1) {
      msg.innerHTML = '<span class="text-success">Nota salva.</span>';
      setTimeout(() => { idx++; render(); }, 250);
    } else {
      msg.innerHTML = '<span class="text-success">Obrigado! Você avaliou todas as análises. 🎉</span>';
    }
  } catch (e) {
    document.querySelectorAll('#nota-row .nota-btn').forEach(b => b.disabled = false);
    msg.innerHTML = `<span class="text-danger">Erro ao salvar: ${escapeHtml(String(e))}</span>`;
  }
}

document.getElementById('btn-anterior').addEventListener('click', () => { if (idx > 0) { idx--; render(); } });
document.getElementById('btn-proxima').addEventListener('click', () => { if (idx < analises.length - 1) { idx++; render(); } });

carregar();
