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
