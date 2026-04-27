const form = document.getElementById('form-analise');
if (form) {
  form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    document.getElementById('form-error').textContent = '';
    const data = Object.fromEntries(new FormData(form).entries());
    // Converter números
    const numericos = [
      'idade','dependentes','tempo_emprego_meses','prazo_meses',
      'score_interno','renegociacoes_recentes',
    ];
    const floats = [
      'renda_anual','valor_solicitado','divida_aberto',
      'area_propriedade_ha','var_produtividade_pct',
    ];
    numericos.forEach(k => data[k] = parseInt(data[k], 10));
    floats.forEach(k => data[k] = parseFloat(data[k]));

    const submitBtn = form.querySelector('button[type=submit]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Analisando...';

    try {
      const r = await fetch('/analise', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
      });
      if (!r.ok) {
        const detail = await r.json().catch(() => ({}));
        throw new Error(detail.detail ? JSON.stringify(detail.detail) : `HTTP ${r.status}`);
      }
      const body = await r.json();
      sessionStorage.setItem('siach.last_resultado', JSON.stringify(body));
      window.location.href = '/static/resultado.html';
    } catch (e) {
      document.getElementById('form-error').textContent = String(e);
      submitBtn.disabled = false;
      submitBtn.textContent = 'Analisar solicitação';
    }
  });
}

const resultadoRoot = document.getElementById('resultado-root');
if (resultadoRoot) {
  const raw = sessionStorage.getItem('siach.last_resultado');
  if (!raw) {
    document.getElementById('conteudo').textContent = 'Nenhum resultado para exibir. Faça uma nova análise.';
  } else {
    const body = JSON.parse(raw);
    document.getElementById('conteudo').innerHTML = renderResultado(body);
    bindFeedbackButtons(body.decisao_id);
  }
}

function renderResultado(body) {
  const pt = body.parecer_tecnico;
  const cls = `recomendacao-${pt.recomendacao}`;
  const similares = body.casos_similares.map(c => `
    <div class="caso-similar">
      <strong>Caso #${c.caso_id}</strong> · decisão original: ${c.decisao_final} · score ${c.score.toFixed(2)}
      <div class="text-muted small mt-1">${escapeHtml(c.narrativa).slice(0, 240)}…</div>
    </div>
  `).join('');

  return `
    <div class="card card-siach p-4 mb-4">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <span class="${cls}">Recomendação: ${pt.recomendacao.replace(/_/g, ' ')}</span>
        <span class="text-muted">Confiança: ${(pt.confianca * 100).toFixed(0)}%</span>
      </div>
      <div class="parecer-humanizado mb-3">${escapeHtml(body.parecer_humanizado)}</div>

      <h5 class="mt-3">Análise técnica</h5>
      <div class="row">
        <div class="col-md-6">
          <h6>Fatores favoráveis</h6>
          <ul>${pt.fatores_favoraveis.map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul>
        </div>
        <div class="col-md-6">
          <h6>Fatores de risco</h6>
          <ul>${pt.fatores_de_risco.map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul>
        </div>
      </div>
      <h6>Comparação histórica</h6>
      <p>${escapeHtml(pt.comparacao_historica)}</p>
      <h6>Recomendações de ação</h6>
      <ul>${pt.recomendacoes_acao.map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul>
    </div>

    <h5>Casos similares consultados</h5>
    ${similares || '<p class="text-muted">Nenhum caso similar.</p>'}

    <div class="mt-4 p-3 bg-white border rounded">
      <h5>Feedback do analista</h5>
      <p class="text-muted small">Aprovar registra este caso na base e o disponibiliza para futuras análises.</p>
      <div class="d-flex gap-2 flex-wrap">
        <button class="btn btn-success" data-feedback="aprovado">Aprovar</button>
        <button class="btn btn-warning" data-feedback="ajustado">Ajustar parecer</button>
        <button class="btn btn-outline-danger" data-feedback="rejeitado">Rejeitar</button>
      </div>
      <div id="feedback-msg" class="mt-2"></div>
      <textarea id="feedback-ajuste" class="form-control mt-2 d-none" rows="3"
        placeholder="Texto revisado pelo analista..."></textarea>
    </div>
  `;
}

function bindFeedbackButtons(decisaoId) {
  const ajusteBox = document.getElementById('feedback-ajuste');
  document.querySelectorAll('[data-feedback]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const status = btn.dataset.feedback;
      if (status === 'ajustado' && ajusteBox.classList.contains('d-none')) {
        ajusteBox.classList.remove('d-none');
        ajusteBox.focus();
        return;
      }
      const payload = { status };
      if (status === 'ajustado') payload.parecer_ajustado = ajusteBox.value;
      const r = await fetch(`/feedback/${decisaoId}`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      const msg = document.getElementById('feedback-msg');
      if (r.ok) {
        msg.innerHTML = `<span class="text-success">Feedback registrado.</span>`;
        document.querySelectorAll('[data-feedback]').forEach(b => b.disabled = true);
      } else {
        const detail = await r.json().catch(() => ({}));
        msg.innerHTML = `<span class="text-danger">Erro: ${escapeHtml(JSON.stringify(detail.detail || ''))}</span>`;
      }
    });
  });
}

function escapeHtml(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[c]);
}

const histRoot = document.getElementById('historico-root');
if (histRoot) {
  fetch('/historico?limit=100').then(r => r.json()).then(items => {
    document.getElementById('historico-conteudo').innerHTML = renderHistorico(items);
  });
}

function renderHistorico(items) {
  if (!items.length) return '<p class="text-muted">Nenhuma análise registrada ainda.</p>';
  return `
    <table class="table table-sm">
      <thead>
        <tr>
          <th>#</th>
          <th>Data</th>
          <th>Atividade</th>
          <th>Valor solicitado</th>
          <th>Recomendação</th>
          <th>Confiança</th>
          <th>Feedback</th>
        </tr>
      </thead>
      <tbody>
        ${items.map(it => `
          <tr>
            <td>${it.id}</td>
            <td>${new Date(it.timestamp).toLocaleString('pt-BR')}</td>
            <td>${escapeHtml(it.dados_solicitante.atividade_principal || '—')}</td>
            <td>R$ ${(it.dados_solicitante.valor_solicitado || 0).toLocaleString('pt-BR')}</td>
            <td><span class="recomendacao-${it.recomendacao}">${it.recomendacao.replace(/_/g, ' ')}</span></td>
            <td>${(it.confianca * 100).toFixed(0)}%</td>
            <td>${escapeHtml(it.status_feedback)}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}
