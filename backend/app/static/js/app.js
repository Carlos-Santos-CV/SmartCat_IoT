let gatoEmEdicaoId = null;
let estacaoEmEdicaoId = null;

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
                <button class="btn-icon" onclick="prepararEdicaoEstacao(${est.id}, '${est.mac_address}', '${est.nome}', '${est.tipo}')" title="Editar">✏️</button>
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

// --- Função Global para Preparar Edição de Estação ---
window.prepararEdicaoEstacao = (id, mac, nome, tipo) => {
  console.log('[CRUD Estações] Preparando edição do ID:', id);
  estacaoEmEdicaoId = id;

  const campoMac = document.getElementById('mac_address');
  campoMac.value = mac || '';
  campoMac.disabled = true; // MAC address não pode ser alterado após vinculado
  document.getElementById('nome_estacao').value = nome || '';
  document.getElementById('tipo_estacao').value = tipo || '';

  const tituloModal = document.getElementById('modal-estacao-titulo');
  if (tituloModal) tituloModal.innerText = 'Editar Estação';

  document.getElementById('modal-estacao').classList.remove('hidden');
};

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
// 🚨 ALERTAS DE SAÚDE
// ======================================================

const ROTULOS_ALERTA = {
  JEJUM: { icone: '⏳', titulo: 'Jejum prolongado' },
  RETENCAO_CAIXA: { icone: '📦', titulo: 'Uso prolongado da caixa' },
  PESO: { icone: '⚖️', titulo: 'Variação de peso' },
};

async function carregarAlertas() {
  const container = document.getElementById('lista-alertas');
  const badge = document.getElementById('alertas-count-badge');
  if (!container) return;

  try {
    const response = await fetch('/api/alertas?apenas_abertos=true');
    const alertas = await response.json();

    if (badge) {
      if (alertas.length > 0) {
        badge.textContent = alertas.length;
        badge.classList.remove('hidden');
      } else {
        badge.classList.add('hidden');
      }
    }

    if (!alertas || alertas.length === 0) {
      container.innerHTML = '<li class="feed-item"><span class="feed-time">✅ Nenhum alerta em aberto. Tudo certo com os pets!</span></li>';
      return;
    }

    container.innerHTML = alertas.map(a => {
      const rotulo = ROTULOS_ALERTA[a.tipo] || { icone: '⚠️', titulo: a.tipo };
      const dataHora = new Date(a.created_at).toLocaleString('pt-BR', {
        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
      });

      return `
        <li class="feed-item feed-item-alerta">
          <div class="feed-info">
            <span class="feed-title">${rotulo.icone} ${rotulo.titulo} • ${a.gato_nome}</span>
            <span class="feed-time">${a.mensagem}</span>
            <span class="feed-time">${dataHora}</span>
          </div>
          <button class="btn-resolver-alerta" onclick="resolverAlerta(${a.id})" title="Marcar como resolvido">✔️</button>
        </li>
      `;
    }).join('');
  } catch (error) {
    console.error('Erro ao buscar alertas:', error);
  }
}

window.resolverAlerta = async (id) => {
  try {
    const res = await fetch(`/api/alertas/${id}/resolver`, { method: 'PUT' });
    if (res.ok) {
      carregarAlertas();
    } else {
      alert('Erro ao resolver alerta.');
    }
  } catch (err) {
    console.error('Erro ao resolver alerta:', err);
  }
};

// ======================================================
// 🥩 ATIVIDADE RECENTE (Refeições + Caixa de Areia)
// ======================================================

async function carregarEventos() {
  const container = document.getElementById('lista-eventos');
  if (!container) return;

  try {
    const response = await fetch('/api/eventos');
    const eventos = await response.json();

    if (!eventos || eventos.length === 0) {
      container.innerHTML = '<li class="feed-item"><span class="feed-time">Nenhuma atividade registrada.</span></li>';
      return;
    }

    container.innerHTML = eventos.map(ev => {
      const dataHora = new Date(ev.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

      if (ev.tipo === 'REFEICAO') {
        return `
          <li class="feed-item feed-item-refeicao">
            <div class="feed-info">
              <span class="feed-title">🥣 Refeição • ${ev.estacao_nome}</span>
              <span class="feed-time">${ev.gato_nome} • ${dataHora}</span>
            </div>
            <div class="feed-value">+${ev.consumo_g}g</div>
          </li>
        `;
      }

      // Evento de Caixa de Areia
      const isAlerta = ev.alerta_retencao;
      return `
        <li class="feed-item ${isAlerta ? 'feed-item-alerta' : 'feed-item-caixa'}">
          <div class="feed-info">
            <span class="feed-title">${isAlerta ? '⚠️ Uso prolongado' : '📦 Caixa de areia'} • ${ev.estacao_nome}</span>
            <span class="feed-time">${ev.gato_nome} • ${dataHora}</span>
          </div>
          <div class="feed-value ${isAlerta ? 'feed-value-alerta' : ''}">${ev.duracao_visita_s}s</div>
        </li>
      `;
    }).join('');
  } catch (error) {
    console.error('Erro ao buscar eventos:', error);
  }
}

// ======================================================
// 🚀 INICIALIZAÇÃO E EVENT LISTENERS
// ======================================================

document.addEventListener('DOMContentLoaded', () => {
  // Carrega os dados iniciais
  carregarGatos();
  carregarEstacoes();
  carregarEventos();
  carregarAlertas();

  // Polling automático para atualizar o feed e os alertas em tempo real
  setInterval(carregarEventos, 5000);
  setInterval(carregarAlertas, 10000);

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
      estacaoEmEdicaoId = null;
      if (formEst) formEst.reset();
      const macField = document.getElementById('mac_address');
      if (macField) macField.disabled = false;
      const tituloModal = document.getElementById('modal-estacao-titulo');
      if (tituloModal) tituloModal.innerText = 'Vincular Estação IoT';
      modalEst.classList.remove('hidden');
    });
  }

  if (btnFecharEst && modalEst) {
    btnFecharEst.addEventListener('click', () => modalEst.classList.add('hidden'));
  }

  if (formEst) {
    formEst.addEventListener('submit', async (e) => {
      e.preventDefault();

      const isEdicaoEst = estacaoEmEdicaoId !== null;

      const estacaoPayload = isEdicaoEst
        ? {
            nome: document.getElementById('nome_estacao').value,
            tipo: document.getElementById('tipo_estacao').value
          }
        : {
            mac_address: document.getElementById('mac_address').value,
            nome: document.getElementById('nome_estacao').value,
            tipo: document.getElementById('tipo_estacao').value
          };

      const urlEst = isEdicaoEst ? `/api/estacoes/${estacaoEmEdicaoId}` : '/api/estacoes';
      const methodEst = isEdicaoEst ? 'PUT' : 'POST';

      console.log(`[CRUD Estações] Enviando ${methodEst} para ${urlEst}`, estacaoPayload);

      try {
        const res = await fetch(urlEst, {
          method: methodEst,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(estacaoPayload)
        });

        if (res.ok) {
          modalEst.classList.add('hidden');
          formEst.reset();
          const macField = document.getElementById('mac_address');
          if (macField) macField.disabled = false;
          estacaoEmEdicaoId = null;
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