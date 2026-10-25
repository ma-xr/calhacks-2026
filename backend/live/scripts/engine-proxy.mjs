// SpacetimeDB refuses module HTTP to private addresses (127.0.0.1, 10/8, 192.168/16, fd00::/8, ...),
// so a locally published module cannot call the engine on localhost. This proxy listens on this
// machine's global IPv6 address and forwards only POST /scenario and GET /health to the engine.
//   node scripts/engine-proxy.mjs          prints the engine url
//   node scripts/engine-proxy.mjs --set    also calls set_engine_url on the local database
// Env: ENGINE_PORT (8787), PROXY_PORT (8788), PROXY_HOST (default: first global IPv6), DB (human-live).
import http from 'node:http';
import os from 'node:os';
import { execFileSync } from 'node:child_process';

const enginePort = Number(process.env.ENGINE_PORT ?? 8787);
const proxyPort = Number(process.env.PROXY_PORT ?? 8788);
const db = process.env.DB ?? 'human-live';
const host = process.env.PROXY_HOST ?? Object.values(os.networkInterfaces()).flat()
  .find(a => a && a.family === 'IPv6' && !a.internal && /^[23]/.test(a.address))?.address;
if (!host) {
  console.error('No global IPv6 address on this machine. Use a tunnel instead (README: "Engine URL").');
  process.exit(1);
}

const allowed = req => (req.method === 'POST' && req.url.startsWith('/scenario?')) ||
  (req.method === 'POST' && req.url === '/scenario') || (req.method === 'GET' && req.url === '/health');

http.createServer((req, res) => {
  if (!allowed(req)) { res.writeHead(403).end('not proxied'); return; }
  const up = http.request({ host: '127.0.0.1', port: enginePort, method: req.method, path: req.url, headers: req.headers }, r => {
    res.writeHead(r.statusCode ?? 502, r.headers);
    r.pipe(res);
  });
  up.on('error', e => { res.writeHead(502).end(`engine: ${e.message}`); });
  req.pipe(up);
}).listen(proxyPort, host, () => {
  const url = `http://[${host}]:${proxyPort}/scenario?lite=1`;
  console.log(`engine proxy: [${host}]:${proxyPort} -> 127.0.0.1:${enginePort}`);
  console.log(`engine url:   ${url}`);
  if (process.argv.includes('--set')) {
    const cli = process.env.SPACETIME ?? `${os.homedir()}/.local/bin/spacetime`;
    execFileSync(cli, ['call', db, 'set_engine_url', JSON.stringify(url), '--server', 'local'], { stdio: 'inherit' });
    console.log(`set_engine_url done on ${db}`);
  }
});
