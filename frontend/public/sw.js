/* BuildingHub service worker — caches only public shell assets, never API/auth/media */
const CACHE = 'buildinghub-shell-v1'
const PRECACHE = ['/', '/index.html', '/manifest.webmanifest', '/offline.html', '/favicon.svg']

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
    ).then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const req = event.request
  const url = new URL(req.url)

  // Never cache API, auth tokens, or private media
  if (url.pathname.startsWith('/api') || url.pathname.includes('/media/')) {
    return
  }
  if (req.method !== 'GET') return

  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok && (url.origin === self.location.origin)) {
          const copy = res.clone()
          caches.open(CACHE).then((cache) => cache.put(req, copy))
        }
        return res
      })
      .catch(async () => {
        const cached = await caches.match(req)
        return cached || caches.match('/offline.html')
      }),
  )
})
