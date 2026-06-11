const analista = decodeURIComponent(location.pathname.split('/').filter(Boolean).pop() || '');
document.getElementById('analista-label').textContent = analista ? `Olá, ${analista}` : '';

// Escala Likert de 5 pontos com rótulos verbais.
const LIKERT = [
  { nota: 1, rotulo: 'Péssima' },
  { nota: 2, rotulo: 'Ruim' },
  { nota: 3, rotulo: 'Regular' },
  { nota: 4, rotulo: 'Boa' },
  { nota: 5, rotulo: 'Ótima' },
];

const PLACEHOLDER_COMENTARIO =
  'Opcional — justifique sua nota se quiser. Ex.: "Acho que a recomendação errou porque…" ' +
  'ou "Concordo, pois…". Anote qualquer observação sobre a análise gerada.';

let analises = [];
let avaliacoes = {};   // { decisao_id: { nota, comentario } }
let idx = 0;
let selecionada = null;  // nota selecionada (ainda não salva) do item atual

function escapeHtml(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[c]);
}

async function carregar() {
  const [a, n] = await Promise.all([
    fetch(`/estudo/analises?analista=${encodeURIComponent(analista)}`).then(r => r.json()),
    fetch(`/avaliacoes/${encodeURIComponent(analista)}`).then(r => r.json()),
  ]);
  analises = a;
  avaliacoes = n;
  if (!analises.length) {
    document.getElementById('conteudo').innerHTML =
      '<p class="text-muted">Nenhuma análise disponível ainda. Volte mais tarde.</p>';
    document.getElementById('progresso').textContent = 'Avaliação';
    document.getElementById('btn-anterior').disabled = true;
    document.getElementById('btn-proxima').disabled = true;
    return;
  }
  const primeiraSemNota = analises.findIndex(x => !(String(x.decisao_id) in avaliacoes));
  idx = primeiraSemNota >= 0 ? primeiraSemNota : 0;
  render();
}

function render() {
  document.getElementById('msg').innerHTML = '';
  const item = analises[idx];
  const pt = item.parecer_tecnico || {};
  const ds = item.dados_solicitante || {};
  const atual = avaliacoes[String(item.decisao_id)] || null;
  selecionada = atual ? atual.nota : null;

  document.getElementById('progresso').textContent = `Análise ${idx + 1} de ${analises.length}`;
  const avaliadas = analises.filter(x => String(x.decisao_id) in avaliacoes).length;
  document.getElementById('contador').textContent = `${avaliadas}/${analises.length} avaliadas`;

  const escala = LIKERT.map(l =>
    `<button class="nota-btn ${selecionada === l.nota ? 'ativa' : ''}" data-nota="${l.nota}">
       <span class="num">${l.nota}</span><span class="lbl">${l.rotulo}</span>
     </button>`
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

      <label class="form-label fw-bold text-success">Como você avalia a qualidade desta análise?</label>
      <div class="likert-row" id="nota-row">${escala}</div>

      <div class="mt-3">
        <label class="form-label fw-bold" for="comentario">Comentário (opcional)</label>
        <textarea id="comentario" class="form-control" rows="3"
          placeholder="${escapeHtml(PLACEHOLDER_COMENTARIO)}">${escapeHtml(atual ? (atual.comentario || '') : '')}</textarea>
      </div>

      <button class="btn btn-success mt-3" id="btn-salvar">Salvar avaliação</button>
    </div>
  `;

  document.querySelectorAll('#nota-row .nota-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      selecionada = parseInt(btn.dataset.nota, 10);
      document.querySelectorAll('#nota-row .nota-btn').forEach(b =>
        b.classList.toggle('ativa', parseInt(b.dataset.nota, 10) === selecionada));
    });
  });
  document.getElementById('btn-salvar').addEventListener('click', () => salvar(item.decisao_id));

  document.getElementById('btn-anterior').disabled = idx === 0;
  // Só permite avançar se a análise atual já foi salva — evita que o analista
  // pule itens sem avaliar (clicando "Próxima" sem salvar).
  const btnProx = document.getElementById('btn-proxima');
  btnProx.disabled = idx >= analises.length - 1 || atual === null;
  btnProx.title = atual === null ? 'Salve a avaliação antes de avançar.' : '';
}

async function salvar(decisaoId) {
  const msg = document.getElementById('msg');
  if (selecionada == null) {
    msg.innerHTML = '<span class="text-danger">Escolha uma nota antes de salvar.</span>';
    return;
  }
  const comentario = document.getElementById('comentario').value.trim() || null;
  const btn = document.getElementById('btn-salvar');
  btn.disabled = true;
  try {
    const r = await fetch('/avaliacoes', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ analista, decisao_id: decisaoId, nota: selecionada, comentario }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    avaliacoes[String(decisaoId)] = { nota: selecionada, comentario };
    if (idx < analises.length - 1) {
      msg.innerHTML = '<span class="text-success">Avaliação salva.</span>';
      setTimeout(() => { idx++; render(); }, 300);
    } else {
      render();
      document.getElementById('msg').innerHTML =
        '<span class="text-success">Obrigado! Você avaliou todas as análises. 🎉</span>';
    }
  } catch (e) {
    btn.disabled = false;
    msg.innerHTML = `<span class="text-danger">Erro ao salvar: ${escapeHtml(String(e))}</span>`;
  }
}

document.getElementById('btn-anterior').addEventListener('click', () => { if (idx > 0) { idx--; render(); } });
document.getElementById('btn-proxima').addEventListener('click', () => {
  const item = analises[idx];
  if (item && !(String(item.decisao_id) in avaliacoes)) {
    document.getElementById('msg').innerHTML =
      '<span class="text-danger">Salve a avaliação desta análise antes de avançar.</span>';
    return;
  }
  if (idx < analises.length - 1) { idx++; render(); }
});

carregar();
