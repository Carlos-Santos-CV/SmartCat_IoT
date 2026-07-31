let gatoEmEdicaoId = null;

// --- Registro do Service Worker ---
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js')
      .then(reg => console.log('[PWA] Service Worker ativo:', reg.scope))
      .catch(err => console.error('[PWA] Erro SW:', err));
  });
}

// ======================================================
// 🐱 PETS (GATOS)
// ======================================================

// --- Listar Gatos ---
async function carregarGatos() {
  const container = document.getElementById('lista-gatos');
  if (!container) return;

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

// --- Funções Globais do Modal de Gatos ---
window.prepararEdicaoGato = (id, tag, nome, nascimento, peso, jejum, caixa) => {
  console.log('[CRUD Gatos] Preparando edição do ID:', id);
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
      console.log('[CRUD Gatos] Excluído com sucesso');
      carregarGatos();
    } else {
      alert('Erro ao excluir pet.');
    }
  } catch (err) {
    console.error('Erro ao deletar gato:', err);
  }
};

// ======================================================
// 📡 ESTAÇÕES IOT
// ======================================================

// --- Listar Estações ---
async function carregarEstacoes() {
  const container = document.getElementById('lista-estacoes');
  if (!container) return;

  try {
    const response = await fetch('/api/estacoes');
    const estacoes = await response.json();

    if (!estacoes || estacoes.length === 0) {
      container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem;">Nenhuma estação vinculada.</p>';
      return;
    }

    container.innerHTML = `
      <div class="gato-grid">
        ${estacoes.map(est => `
          <div class="gato-card">
            <div class="gato-card-header">
              <h3>${est.tipo === 'COMIDA' ? '🥣' : '📦'} ${est.nome}</h3>
              <div class="gato-actions">
                <button class="btn-icon" onclick="deletarEstacao(${est.id}, '${est.nome}')" title="Excluir">🗑️</button>
              </div>
            </div>
            <p><strong>ID:</strong> ${est.mac_address}</p>
            <p><strong>Tipo:</strong> ${est.tipo === 'COMIDA' ? 'Alimentador' : 'Sanitário'}</p>
          </div>
        `).join('')}
      </div>
    `;
  } catch (error) {
    console.error('Erro ao buscar estações:', error);
  }
}

// --- Função Global para Deletar Estação ---
window.deletarEstacao = async (id, nome) => {
  if (!confirm(`Deseja desvincular a estação "${nome}"?`)) return;

  try {
    const res = await fetch(`/api/estacoes/${id}`, { method: 'DELETE' });
    if (res.ok) {
      console.log('[CRUD Estações] Estação desvinculada');
      carregarEstacoes();
    } else {
      alert('Erro ao excluir estação.');
    }
  } catch (err) {
    console.error('Erro ao deletar estação:', err);
  }
};

// ======================================================
// 🥩 HISTÓRICO DE REFEIÇÕES
// ======================================================

async function carregarRefeicoes() {
  const container = document.getElementById('lista-refeicoes');
  if (!container) return;

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

// ======================================================
// 🚀 INICIALIZAÇÃO E EVENT LISTENERS
// ======================================================

document.addEventListener('DOMContentLoaded', () => {
  // Carrega os dados iniciais
  carregarGatos();
  carregarEstacoes();
  carregarRefeicoes();

  // Polling automático para atualizar refeições em tempo real
  setInterval(carregarRefeicoes, 5000);

  // --- CONTROLE DO MODAL DE GATOS ---
  const modalGato = document.getElementById('modal-gato');
  const btnAbrirGato = document.getElementById('btn-abrir-modal');
  const btnFecharGato = document.getElementById('btn-fechar-modal');
  const formGato = document.getElementById('form-gato');

  if (btnAbrirGato && modalGato) {
    btnAbrirGato.addEventListener('click', () => {
      gatoEmEdicaoId = null;
      if (formGato) formGato.reset();
      const tituloModal = document.getElementById('modal-titulo');
      if (tituloModal) tituloModal.innerText = 'Cadastrar Novo Pet';
      modalGato.classList.remove('hidden');
    });
  }

  if (btnFecharGato && modalGato) {
    btnFecharGato.addEventListener('click', () => modalGato.classList.add('hidden'));
  }

  if (formGato) {
    formGato.addEventListener('submit', async (e) => {
      e.preventDefault();

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

      console.log(`[CRUD Gatos] Enviando ${method} para ${url}`, gatoPayload);

      try {
        const res = await fetch(url, {
          method: method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(gatoPayload)
        });

        if (res.ok) {
          modalGato.classList.add('hidden');
          formGato.reset();
          gatoEmEdicaoId = null;
          carregarGatos();
        } else {
          const errData = await res.json();
          alert('Erro ao salvar pet: ' + (errData.detail || 'Verifique os dados enviados.'));
        }
      } catch (err) {
        console.error('[CRUD Gatos] Erro de rede:', err);
        alert('Erro de conexão ao salvar pet.');
      }
    });
  }

  // --- CONTROLE DO MODAL DE ESTAÇÕES ---
  const modalEst = document.getElementById('modal-estacao');
  const btnAbrirEst = document.getElementById('btn-abrir-modal-estacao');
  const btnFecharEst = document.getElementById('btn-fechar-modal-estacao');
  const formEst = document.getElementById('form-estacao');

  if (btnAbrirEst && modalEst) {
    btnAbrirEst.addEventListener('click', () => {
      if (formEst) formEst.reset();
      modalEst.classList.remove('hidden');
    });
  }

  if (btnFecharEst && modalEst) {
    btnFecharEst.addEventListener('click', () => modalEst.classList.add('hidden'));
  }

  if (formEst) {
    formEst.addEventListener('submit', async (e) => {
      e.preventDefault();

      const estacaoPayload = {
        mac_address: document.getElementById('mac_address').value,
        nome: document.getElementById('nome_estacao').value,
        tipo: document.getElementById('tipo_estacao').value
      };

      console.log('[CRUD Estações] Enviando POST para /api/estacoes', estacaoPayload);

      try {
        const res = await fetch('/api/estacoes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(estacaoPayload)
        });

        if (res.ok) {
          modalEst.classList.add('hidden');
          formEst.reset();
          carregarEstacoes();
        } else {
          const errData = await res.json();
          alert('Erro ao vincular estação: ' + (errData.detail || 'Verifique os dados.'));
        }
      } catch (err) {
        console.error('[CRUD Estações] Erro de rede:', err);
        alert('Erro de conexão ao salvar estação.');
      }
    });
  }
});