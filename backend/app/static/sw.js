// Service Worker do SmartCat PWA
const CACHE_NAME = 'smartcat-v1';

// Evento de Instalação do Service Worker
self.addEventListener('install', (event) => {
  console.log('[SW] Service Worker Instalado com Sucesso!');
  self.skipWaiting();
});

// Evento de Ativação
self.addEventListener('activate', (event) => {
  console.log('[SW] Service Worker Ativo!');
});

// ESCUTADOR DE NOTIFICAÇÕES PUSH (Disparadas pelo backend Python)
self.addEventListener('push', (event) => {
  let data = { title: 'Alerta SmartCat', body: 'Nova atualização de saúde!' };
  
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-192.png',
    vibrate: [200, 100, 200],
    data: data.data || {}
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Clique na Notificação Push
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow('/')
  );
});