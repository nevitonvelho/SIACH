const token = new URLSearchParams(location.search).get('token') || '';
document.getElementById('link-csv').href = `/resultados.csv?token=${encodeURIComponent(token)}`;

function escapeHtml(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[c]);
}

async function carregar() {
  const r = await fetch(`/resultados/dados?token=${encodeURIComponent(token)}`);
  const cont = document.getElementById('conteudo');
  if (r.status === 403) { cont.innerHTML = '<p class="text-danger">Token inválido. Use /resultados?token=SEU_TOKEN</p>'; return; }
  const d = await r.json();

  const linhasAnalise = d.por_analise.map(p => `
    <tr>
      <td>${escapeHtml(p.analista ?? '—')}</td>
      <td>${p.ordem}</td>
      <td>${p.decisao_id}</td>
      <td><span class="recomendacao-${p.recomendacao}">${String(p.recomendacao).replace(/_/g,' ')}</span></td>
      <td><strong>${p.media ?? '—'}</strong></td>
      <td>${p.n_notas}</td>
    </tr>`).join('');

  const linhasAnalista = d.por_analista.map(p => `
    <tr>
      <td>${escapeHtml(p.analista)}</td>
      <td><strong>${p.media ?? '—'}</strong></td>
      <td>${p.avaliadas}/${p.atribuidas ?? '—'}</td>
      <td>${p.faltam}</td>
    </tr>`).join('');

  cont.innerHTML = `
    <h2 class="h5">Por análise (${d.total_itens})</h2>
    <table class="table table-sm">
      <thead><tr><th>Analista</th><th>Ordem</th><th>Decisão</th><th>Recomendação</th><th>Nota média</th><th>Nº notas</th></tr></thead>
      <tbody>${linhasAnalise || '<tr><td colspan="6" class="text-muted">Sem itens.</td></tr>'}</tbody>
    </table>
    <h2 class="h5 mt-4">Por analista</h2>
    <table class="table table-sm">
      <thead><tr><th>Analista</th><th>Nota média</th><th>Avaliadas</th><th>Faltam</th></tr></thead>
      <tbody>${linhasAnalista || '<tr><td colspan="4" class="text-muted">Nenhuma avaliação ainda.</td></tr>'}</tbody>
    </table>
  `;
}

carregar();
