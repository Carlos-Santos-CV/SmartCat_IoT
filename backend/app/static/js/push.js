// ======================================================
// 🔔 SmartCat — Notificações Web Push
// ======================================================
// Responsável por: pedir permissão ao usuário, inscrever/desinscrever o
// navegador no Push Service usando a chave pública VAPID do servidor, e
// manter o toggle switch sincronizado com o estado real da inscrição.

// Converte a chave pública VAPID (base64url) para o formato Uint8Array
// exigido pela PushManager.subscribe().
function urlBase64ToUint8Array(base64String) {
  const cleanKey = base64String.trim().replace(/\s+/g, '');
  // Converte de base64url para base64 padrão
  let base64 = cleanKey.replace(/-/g, '+').replace(/_/g, '/');
  // Adiciona padding se necessário
  while (base64.length % 4) {
    base64 += '=';
  }
  const binaryString = window.atob(base64);
  const outputArray = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    outputArray[i] = binaryString.charCodeAt(i);
  }
  return outputArray;
}

// Sincroniza a aparência do toggle (posição do switch + texto) com o
// estado real de inscrição do navegador.
async function atualizarStatusNotificacoes() {
  const controle = document.getElementById('notif-control');
  const btn = document.getElementById('btn-ativar-notificacoes');
  const textoStatus = document.getElementById('notif-status-text');
  const btnTeste = document.getElementById('btn-testar-notificacao');

  if (!btn || !('serviceWorker' in navigator) || !('PushManager' in window)) {
    if (controle) controle.classList.add('hidden');
    if (btnTeste) btnTeste.classList.add('hidden');
    return;
  }

  try {
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    const ativo = !!sub;

    btn.setAttribute('aria-checked', String(ativo));
    btn.setAttribute('aria-label', ativo ? 'Desativar notificações push' : 'Ativar notificações push');

    if (textoStatus) {
      textoStatus.textContent = ativo ? 'Ativadas' : 'Desativadas';
      textoStatus.classList.toggle('notif-status-text-ativo', ativo);
    }

    if (btnTeste) btnTeste.classList.toggle('hidden', !ativo);
  } catch (err) {
    console.error('[PUSH] Erro ao checar inscrição:', err);
  }
}

// Liga/desliga as notificações — o mesmo botão faz os dois sentidos,
// dependendo do estado atual da inscrição.
async function alternarNotificacoesPush() {
  const btn = document.getElementById('btn-ativar-notificacoes');

  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    alert('Seu navegador não tem suporte a notificações push.');
    return;
  }

  if (btn) btn.disabled = true;

  try {
    const reg = await navigator.serviceWorker.ready;
    let sub = await reg.pushManager.getSubscription();

    if (sub) {
      // --- Já está ativo: desliga ---
      await fetch('/api/push/unsubscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sub.toJSON()),
      }).catch(() => {}); // mesmo se a chamada falhar, ainda desinscreve localmente

      await sub.unsubscribe();
      console.log('[PUSH] Notificações desativadas.');
      return;
    }

    // --- Está desligado: liga ---
    const permissao = await Notification.requestPermission();
    if (permissao !== 'granted') {
      alert('Permissão de notificações negada. Você não receberá alertas de saúde.');
      return;
    }

    const resChave = await fetch('/api/push/vapid-public-key');
    if (!resChave.ok) {
      alert('O servidor ainda não configurou as notificações push (chave VAPID ausente).');
      return;
    }
    const { publicKey } = await resChave.json();

    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });

    const resInscricao = await fetch('/api/push/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sub.toJSON()),
    });

    if (!resInscricao.ok) {
      alert('Erro ao registrar inscrição de notificações no servidor.');
    } else {
      console.log('[PUSH] Inscrição registrada com sucesso.');
    }
  } catch (err) {
    console.error('[PUSH] Erro ao alternar notificações:', err);
    alert('Não foi possível alterar o estado das notificações push.');
  } finally {
    if (btn) btn.disabled = false;
    atualizarStatusNotificacoes();
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

document.addEventListener('DOMContentLoaded', () => {
  atualizarStatusNotificacoes();

  const btn = document.getElementById('btn-ativar-notificacoes');
  if (btn) {
    btn.addEventListener('click', alternarNotificacoesPush);
  }

  const btnTeste = document.getElementById('btn-testar-notificacao');
  if (btnTeste) {
    btnTeste.addEventListener('click', enviarNotificacaoTeste);
  }
});
