const CACHE = "iddaatakip-v14";
const OFFLINE_ASSETS = [
  "./",
  "./index.html",
  "./icons/icon-192.png",
  "./icons/icon-512.png"
];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(OFFLINE_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", e => {
  // Sadece GET isteklerini yakala
  if (e.request.method !== "GET") return;
  e.respondWith(
    fetch(e.request)
      .then(res => {
        // Başarılı cevabı cache'e yaz
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});

// PWA WEB PUSH NOTIFICATION HANDLERS
self.addEventListener("push", e => {
  let data = {
    title: "İddaa Takip",
    body: "Canlı maç güncellemesi",
    icon: "icons/icon-192.png",
    badge: "icons/icon-192.png",
    url: "./"
  };

  if (e.data) {
    try {
      const parsed = e.data.json();
      data = { ...data, ...parsed };
    } catch (err) {
      data.body = e.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: data.icon || "icons/icon-192.png",
    badge: data.badge || "icons/icon-192.png",
    vibrate: [250, 100, 250, 100, 250],
    data: { url: data.url || "./" },
    tag: data.tag || ("iddaatakip-" + Date.now()),
    renotify: true
  };

  const title = data.title || "İddaa Takip";

  e.waitUntil(
    self.registration.showNotification(title, options)
  );
});

self.addEventListener("notificationclick", e => {
  e.notification.close();
  const targetUrl = e.notification.data?.url || "./";
  e.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then(windowClients => {
      for (const client of windowClients) {
        if ("focus" in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});
