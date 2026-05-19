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

http.createServer((req, res) => {
  // Strip query string
  const urlPath = req.url.split('?')[0]
  let filePath = path.join(dist, urlPath)

  // If file doesn't exist and it's not a static asset, serve index.html (SPA fallback)
  const ext = path.extname(filePath)
  if (!fs.existsSync(filePath) && !ext) {
    filePath = path.join(dist, 'index.html')
  }

  const contentType = mimeTypes[path.extname(filePath)] || 'text/plain'

  fs.readFile(filePath, (err, data) => {
    if (err) {
      // Final fallback
      const fallback = path.join(dist, 'index.html')
      fs.readFile(fallback, (err2, data2) => {
        if (err2) {
          res.writeHead(404)
          res.end('Not found')
        } else {
          res.writeHead(200, { 'Content-Type': 'text/html' })
          res.end(data2)
        }
      })
    } else {
      res.writeHead(200, { 'Content-Type': contentType })
      res.end(data)
    }
  })
}).listen(port, '0.0.0.0', () => {
  console.log(`Serving SynapseCode on http://localhost:${port}`)
})
