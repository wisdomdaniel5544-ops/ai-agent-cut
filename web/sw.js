// minimal service worker: cache the app shell so the PWA installs/opens offline (jobs still need the backend)
const C='aac-v1';self.addEventListener('install',e=>e.waitUntil(caches.open(C).then(c=>c.addAll(['/','/static/icon.svg','/manifest.webmanifest']))));
self.addEventListener('fetch',e=>{if(e.request.method!=='GET'||new URL(e.request.url).pathname.startsWith('/api')||e.request.url.includes('/files/'))return;
 e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)))});
