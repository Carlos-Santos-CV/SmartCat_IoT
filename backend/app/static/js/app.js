if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js')
      .then(reg => console.log('[PWA] Service Worker ativo:', reg.scope))
      .catch(err => console.error('[PWA] Erro no Service Worker:', err));
  });
}

async function carregarGatos() {
  const container = document.getElementById('lista-gatos');
  try {
    const response = await fetch('/api/gatos');
    const gatos = await response.json();

    if (!gatos || gatos.length === 0) {
      container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem;">Nenhum gato cadastrado.</p>';
      return;
    }

    container.innerHTML = `
      <div class="gato-grid">
        ${gatos.map(gato => `
          <div class="gato-card">
            <h3>🐱 ${gato.nome}</h3>
            <p><strong>RFID:</strong> ${gato.tag_rfid}</p>
            <p>Jejum: ${gato.limite_jejum_horas}h | Caixa: ${gato.limite_caixa_segundos}s</p>
          </div>
        `).join('')}
      </div>
    `;
  } catch (error) {
    console.error('Erro ao buscar gatos:', error);
  }
}

async function carregarRefeicoes() {
  const container = document.getElementById('lista-refeicoes');
  try {
    const response = await fetch('/api/refeicoes');
    const refeicoes = await response.json();

    if (!refeicoes || refeicoes.length === 0) {
      container.innerHTML = '<li class="feed-item"><span class="feed-time">Nenhuma refeição registrada.</span></li>';
      return;
    }

    container.innerHTML = refeicoes.map(ref => {
      const dataHora = new Date(ref.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
      return `
        <li class="feed-item">
          <div class="feed-info">
            <span class="feed-title">Refeição Confirmada</span>
            <span class="feed-time">Tag: ${ref.gato_tag} • ${dataHora}</span>
          </div>
          <div class="feed-value">+${ref.consumo_g}g</div>
        </li>
      `;
    }).join('');
  } catch (error) {
    console.error('Erro ao buscar refeições:', error);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  carregarGatos();
  carregarRefeicoes();
  setInterval(carregarRefeicoes, 5000);

  const modal = document.getElementById('modal-gato');
  const btnAbrir = document.getElementById('btn-abrir-modal');
  const btnFechar = document.getElementById('btn-fechar-modal');
  const form = document.getElementById('form-gato');

  if (btnAbrir && modal) {
    btnAbrir.addEventListener('click', () => modal.classList.remove('hidden'));
  }
  if (btnFechar && modal) {
    btnFechar.addEventListener('click', () => modal.classList.add('hidden'));
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const novoGato = {
        tag_rfid: document.getElementById('tag_rfid').value,
        nome: document.getElementById('nome').value,
        data_nascimento: document.getElementById('data_nascimento').value,
        peso_meta_g: parseFloat(document.getElementById('peso_meta_g').value),
        limite_jejum_horas: parseInt(document.getElementById('limite_jejum_horas').value),
        limite_caixa_segundos: parseInt(document.getElementById('limite_caixa_segundos').value)
      };

      try {
        const res = await fetch('/api/gatos', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(novoGato)
        });

        if (res.ok) {
          modal.classList.add('hidden');
          form.reset();
          carregarGatos();
        } else {
          const errData = await res.json();
          alert('Erro: ' + (errData.detail || 'Falha ao cadastrar pet.'));
        }
      } catch (err) {
        console.error('Erro no cadastro:', err);
      }
    });
  }
});