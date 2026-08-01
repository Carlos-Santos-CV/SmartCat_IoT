// ======================================================
// 🔔 SmartCat — Notificações Web Push
// ======================================================
// Responsável por: pedir permissão ao usuário, inscrever o navegador
// no Push Service usando a chave pública VAPID do servidor, e enviar
// essa inscrição para o backend salvar (POST /api/push/subscribe).

// Converte a chave pública VAPID (base64url) para o formato Uint8Array
// exigido pela PushManager.subscribe().
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

// Verifica se o navegador já está inscrito e atualiza o texto do botão.
async function atualizarStatusNotificacoes() {
  const btn = document.getElementById('btn-ativar-notificacoes');
  const btnTeste = document.getElementById('btn-testar-notificacao');
  if (!btn || !('serviceWorker' in navigator) || !('PushManager' in window)) {
    if (btn) btn.style.display = 'none';
    if (btnTeste) btnTeste.classList.add('hidden');
    return;
  }

  try {
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    btn.textContent = sub ? '🔔 Notificações ativadas' : '🔕 Ativar notificações';
    btn.classList.toggle('btn-notif-ativo', !!sub);
    if (btnTeste) btnTeste.classList.toggle('hidden', !sub);
  } catch (err) {
    console.error('[PUSH] Erro ao checar inscrição:', err);
  }
}

// Dispara uma notificação de teste via backend, pra debug rápido.
async function enviarNotificacaoTeste() {
  const btnTeste = document.getElementById('btn-testar-notificacao');
  if (btnTeste) {
    btnTeste.disabled = true;
    btnTeste.textContent = '🧪 Enviando...';
  }

  try {
    const res = await fetch('/api/push/test', { method: 'POST' });
    const data = await res.json();

    if (!res.ok) {
      alert(data.detail || 'Erro ao enviar notificação de teste.');
      return;
    }

    console.log('[PUSH] Teste enviado:', data);
  } catch (err) {
    console.error('[PUSH] Erro ao enviar notificação de teste:', err);
    alert('Não foi possível contatar o servidor para o teste.');
  } finally {
    if (btnTeste) {
      btnTeste.disabled = false;
      btnTeste.textContent = '🧪 Enviar teste';
    }
  }
}

// Fluxo principal: pede permissão, inscreve e envia ao backend.
async function ativarNotificacoesPush() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    alert('Seu navegador não tem suporte a notificações push.');
    return;
  }

  try {
    const permissao = await Notification.requestPermission();
    if (permissao !== 'granted') {
      alert('Permissão de notificações negada. Você não receberá alertas de saúde.');
      return;
    }

    // Busca a chave pública VAPID no backend
    const resChave = await fetch('/api/push/vapid-public-key');
    if (!resChave.ok) {
      alert('O servidor ainda não configurou as notificações push (chave VAPID ausente).');
      return;
    }
    const { publicKey } = await resChave.json();

    const reg = await navigator.serviceWorker.ready;

    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });
    }

    const resInscricao = await fetch('/api/push/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sub.toJSON()),
    });

    if (resInscricao.ok) {
      console.log('[PUSH] Inscrição registrada com sucesso.');
      atualizarStatusNotificacoes();
    } else {
      alert('Erro ao registrar inscrição de notificações no servidor.');
    }
  } catch (err) {
    console.error('[PUSH] Erro ao ativar notificações:', err);
    alert('Não foi possível ativar as notificações push.');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  atualizarStatusNotificacoes();

  const btn = document.getElementById('btn-ativar-notificacoes');
  if (btn) {
    btn.addEventListener('click', ativarNotificacoesPush);
  }

  const btnTeste = document.getElementById('btn-testar-notificacao');
  if (btnTeste) {
    btnTeste.addEventListener('click', enviarNotificacaoTeste);
  }
});
