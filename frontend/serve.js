// 前端静态文件服务 + API 代理（生产部署用）
// 将 /api/v1 请求转发到后端 http://localhost:8000
// 将 /api/v1/video 请求转发到 AI Tutor http://localhost:8001
// 使用方法：先 npm run build，再 node serve.js
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 5173;
const BACKEND = 'http://localhost:8000';
const AI_TUTOR = 'http://localhost:8001';
const DIST_DIR = path.join(__dirname, 'dist');

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'application/javascript; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg':  'image/svg+xml',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.ico':  'image/x-icon',
  '.woff': 'font/woff',
  '.woff2':'font/woff2',
  '.ttf':  'font/ttf',
};

const server = http.createServer((req, res) => {
  // AI Tutor 视频相关 API 请求
  if (req.url.startsWith('/api/v1/video') || req.url.startsWith('/static/videos')) {
    const url = new URL(req.url, AI_TUTOR);
    let proxyPath = url.pathname + url.search;
    // 去掉 /api/v1 前缀
    if (proxyPath.startsWith('/api/v1/video')) {
      proxyPath = proxyPath.replace(/^\/api\/v1/, '/api');
    }
    const options = {
      hostname: 'localhost',
      port: 8001,
      path: proxyPath,
      method: req.method,
      headers: { ...req.headers, host: 'localhost:8001' },
    };

    const proxy = http.request(options, (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    });

    proxy.on('error', () => {
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'AI Tutor 服务不可用' }));
    });

    req.pipe(proxy);
    return;
  }

  // 后端 API 请求转发
  if (req.url.startsWith('/api/')) {
    const url = new URL(req.url, BACKEND);
    const options = {
      hostname: 'localhost',
      port: 8000,
      path: url.pathname + url.search,
      method: req.method,
      headers: { ...req.headers, host: 'localhost:8000' },
    };

    const proxy = http.request(options, (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    });

    proxy.on('error', () => {
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: '后端服务不可用，请确认后端已启动' }));
    });

    req.pipe(proxy);
    return;
  }

  // 静态文件服务
  let filePath = path.join(DIST_DIR, req.url === '/' ? 'index.html' : req.url);

  // SPA: 未匹配的路径返回 index.html
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    const tryPath = path.join(DIST_DIR, req.url);
    if (fs.existsSync(tryPath) && !fs.statSync(tryPath).isDirectory()) {
      filePath = tryPath;
    } else {
      filePath = path.join(DIST_DIR, 'index.html');
    }
  }

  const ext = path.extname(filePath);
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end('Not Found');
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(data);
    }
  });
});

// 检查 dist 目录是否存在
if (!fs.existsSync(DIST_DIR) || !fs.existsSync(path.join(DIST_DIR, 'index.html'))) {
  console.error('\n  [错误] dist/ 目录不存在或未构建');
  console.error('  请先运行: npm run build\n');
  process.exit(1);
}

server.listen(PORT, () => {
  console.log(`\n  AI Learning System 前端服务已启动`);
  console.log(`  访问地址: http://localhost:${PORT}\n`);
  console.log(`  API 代理: /api/v1/* → ${BACKEND}/api/v1/*`);
  console.log(`  AI Tutor: /api/v1/video/* → ${AI_TUTOR}/api/video/*\n`);
});
