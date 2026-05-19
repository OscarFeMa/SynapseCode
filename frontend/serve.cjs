const http = require('http')
const fs = require('fs')
const path = require('path')

const dist = path.join(__dirname, 'dist')
const port = 5173

const mimeTypes = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.json': 'application/json',
  '.map': 'application/json',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
}

function serveFile(filePath, res) {
  const ext = path.extname(filePath)
  const contentType = mimeTypes[ext] || 'text/plain'
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404)
      res.end('Not found')
    } else {
      res.writeHead(200, { 'Content-Type': contentType })
      res.end(data)
    }
  })
}

http.createServer((req, res) => {
  const urlPath = req.url.split('?')[0]

  // /app/* → servir desde dist/ (React SPA build)
  if (urlPath.startsWith('/app')) {
    const appPath = urlPath.replace('/app', '') || '/index.html'
    const filePath = path.join(__dirname, 'dist', appPath)
    if (!fs.existsSync(filePath) || !path.extname(filePath)) {
      return serveFile(path.join(__dirname, 'dist', 'index.html'), res)
    }
    return serveFile(filePath, res)
  }

  // / → landing page
  const webPath = path.join(__dirname, 'web', urlPath === '/' ? 'index.html' : urlPath)
  if (fs.existsSync(webPath) && fs.statSync(webPath).isFile()) {
    return serveFile(webPath, res)
  }

  // Fallback → landing
  serveFile(path.join(__dirname, 'web', 'index.html'), res)
}).listen(port, '0.0.0.0', () => {
  console.log(`Serving SynapseCode on http://localhost:${port}`)
  console.log(`Landing page: http://localhost:${port}/`)
  console.log(`React App: http://localhost:${port}/app/`)
})
