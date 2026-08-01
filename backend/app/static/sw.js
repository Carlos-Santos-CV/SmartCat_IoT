// Service Worker do SmartCat PWA
const CACHE_NAME = 'smartcat-shell-v2';

// Evento de Instalação do Service Worker
self.addEventListener('install', (event) => {
  console.log('[SW] Service Worker Instalado com Sucesso!');
  self.skipWaiting();
});

// Evento de Ativação — limpa caches de versões antigas
self.addEventListener('activate', (event) => {
  console.log('[SW] Service Worker Ativo!');
  event.waitUntil(
    caches.keys().then((nomes) =>
      Promise.all(
        nomes
          .filter((nome) => nome !== CACHE_NAME)
          .map((nome) => caches.delete(nome))
      )
    ).then(() => self.clients.claim())
  );
});

// ESCUTADOR DE REQUISIÇÕES — cache-runtime com fallback de rede,
// para o app abrir mesmo offline/sem sinal. Chamadas à API (dados
// dinâmicos) não são interceptadas: seguem sempre direto pra rede.
self.addEventListener('fetch', (event) => {
  const { request } = event;

  if (request.method !== 'GET' || request.url.includes('/api/')) {
    return; // deixa o navegador tratar normalmente
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      const buscaNaRede = fetch(request)
        .then((response) => {
          if (response && response.ok) {
            const copia = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copia));
          }
          return response;
        })
        .catch(() => cached);

      return cached || buscaNaRede;
    })
  );
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