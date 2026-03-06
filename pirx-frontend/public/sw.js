// PIRX Service Worker for Push Notifications & Offline Caching
const CACHE_NAME = "pirx-v1";
const PROJECTION_CACHE = "pirx-projections";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k !== CACHE_NAME && k !== PROJECTION_CACHE)
            .map((k) => caches.delete(k))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  if (url.pathname.includes("/projection") && event.request.method === "GET") {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const clone = response.clone();
          caches.open(PROJECTION_CACHE).then((cache) => {
            cache.put(event.request, clone);
          });
          return response;
        })
        .catch(() => {
          return caches.match(event.request);
        })
    );
    return;
  }
});

self.addEventListener("push", (event) => {
  const data = event.data?.json() ?? {};
  const title = data.title || "PIRX Update";
  const options = {
    body: data.body || "",
    icon: "/icon-192.png",
    badge: "/icon-72.png",
    tag: data.notification_type || "pirx",
    data: { deep_link: data.deep_link || "/" },
    vibrate: [100, 50, 100],
    actions: [{ action: "open", title: "View" }],
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const deepLink = event.notification.data?.deep_link || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window" }).then((clients) => {
      for (const client of clients) {
        if (client.url.includes(self.location.origin) && "focus" in client) {
          client.navigate(deepLink);
          return client.focus();
        }
      }
      return self.clients.openWindow(deepLink);
    })
  );
});
