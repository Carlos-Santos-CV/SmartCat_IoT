let gatoEmEdicaoId = null;

// --- Registro do Service Worker ---
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js')
      .then(reg => console.log('[PWA] Service Worker ativo:', reg.scope))
      .catch(err => console.error('[PWA] Erro SW:', err));
  });
}

// --- Listar Gatos ---
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
            <div class="gato-card-header">
              <h3>🐱 ${gato.nome}</h3>
              <div class="gato-actions">
                <button class="btn-icon" onclick="prepararEdicaoGato(${gato.id}, '${gato.tag_rfid}', '${gato.nome}', '${gato.data_nascimento}', ${gato.peso_meta_g}, ${gato.limite_jejum_horas}, ${gato.limite_caixa_segundos})" title="Editar">✏️</button>
                <button class="btn-icon" onclick="deletarGato(${gato.id}, '${gato.nome}')" title="Excluir">🗑️</button>
              </div>
            </div>
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

// --- Listar Refeições ---
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

// --- Funções Globais do Modal ---
window.prepararEdicaoGato = (id, tag, nome, nascimento, peso, jejum, caixa) => {
  console.log('[CRUD] Preparando edição do gato ID:', id);
  gatoEmEdicaoId = id;

  document.getElementById('tag_rfid').value = tag || '';
  document.getElementById('nome').value = nome || '';
  document.getElementById('data_nascimento').value = nascimento || '';
  document.getElementById('peso_meta_g').value = peso || 4000;
  document.getElementById('limite_jejum_horas').value = jejum || 24;
  document.getElementById('limite_caixa_segundos').value = caixa || 300;

  const tituloModal = document.getElementById('modal-titulo');
  if (tituloModal) tituloModal.innerText = 'Editar Pet';

  document.getElementById('modal-gato').classList.remove('hidden');
};

window.deletarGato = async (id, nome) => {
  if (!confirm(`Tem certeza que deseja excluir o pet "${nome}"?`)) return;

  try {
    const res = await fetch(`/api/gatos/${id}`, { method: 'DELETE' });
    if (res.ok) {
      console.log('[CRUD] Gato excluído com sucesso');
      carregarGatos();
    } else {
      alert('Erro ao excluir pet.');
    }
  } catch (err) {
    console.error('Erro ao deletar:', err);
  }
};

// --- Inicialização e Controle de Eventos ---
document.addEventListener('DOMContentLoaded', () => {
  carregarGatos();
  carregarRefeicoes();
  setInterval(carregarRefeicoes, 5000);

  const modal = document.getElementById('modal-gato');
  const btnAbrir = document.getElementById('btn-abrir-modal');
  const btnFechar = document.getElementById('btn-fechar-modal');
  const form = document.getElementById('form-gato');

  if (btnAbrir) {
    btnAbrir.addEventListener('click', () => {
      gatoEmEdicaoId = null;
      if (form) form.reset();
      const tituloModal = document.getElementById('modal-titulo');
      if (tituloModal) tituloModal.innerText = 'Cadastrar Novo Pet';
      modal.classList.remove('hidden');
    });
  }

  if (btnFechar) {
    btnFechar.addEventListener('click', () => modal.classList.add('hidden'));
  }

  // Intercepção do Submit
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault(); // Previne o reload padrão da página

      const gatoPayload = {
        tag_rfid: document.getElementById('tag_rfid').value,
        nome: document.getElementById('nome').value,
        data_nascimento: document.getElementById('data_nascimento').value,
        peso_meta_g: parseFloat(document.getElementById('peso_meta_g').value) || 0,
        limite_jejum_horas: parseInt(document.getElementById('limite_jejum_horas').value) || 24,
        limite_caixa_segundos: parseInt(document.getElementById('limite_caixa_segundos').value) || 300
      };

      const isEdicao = gatoEmEdicaoId !== null;
      const url = isEdicao ? `/api/gatos/${gatoEmEdicaoId}` : '/api/gatos';
      const method = isEdicao ? 'PUT' : 'POST';

      console.log(`[CRUD] Enviando requisição ${method} para ${url}`, gatoPayload);

      try {
        const res = await fetch(url, {
          method: method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(gatoPayload)
        });

        if (res.ok) {
          console.log('[CRUD] Salvo com sucesso!');
          modal.classList.add('hidden');
          form.reset();
          gatoEmEdicaoId = null;
          carregarGatos();
        } else {
          const errData = await res.json();
          console.error('[CRUD] Erro do servidor:', errData);
          alert('Erro ao salvar: ' + (errData.detail || 'Verifique os dados enviados.'));
        }
      } catch (err) {
        console.error('[CRUD] Erro de rede:', err);
        alert('Erro de conexão ao salvar pet.');
      }
    });
  }
});