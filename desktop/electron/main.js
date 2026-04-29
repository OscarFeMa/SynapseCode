const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');
const dgram = require('dgram');
const express = require('express');
const winrm = require('node-winrm');

let mainWindow;
let masterProcess = null;
let workerProcess = null;
let discoverySocket = null;
let localServer = null;

// Configuration
const MASTER_PORT = 8000;
const DISCOVERY_PORT = 54321;
const BACKEND_PATH = path.join(__dirname, '../../backend');
const LOCAL_SERVER_PORT = 5174;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    backgroundColor: '#0F172A',
    show: true,
    maximized: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    },
    icon: path.join(__dirname, '../assets/icon.png'),
    autoHideMenuBar: true
  });

  // Load the app
  const isDev = !app.isPackaged;
  
  if (isDev) {
    // Load from dev server
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    // In production, start a local Express server to serve the frontend
    const frontendPath = path.join(process.resourcesPath, 'frontend', 'dist');
    console.log('Frontend path:', frontendPath);
    console.log('Frontend exists:', require('fs').existsSync(frontendPath));
    
    // Start Express server
    const appExpress = express();
    appExpress.use(express.static(frontendPath));
    
    localServer = appExpress.listen(LOCAL_SERVER_PORT, () => {
      console.log(`Local server running on port ${LOCAL_SERVER_PORT}`);
      mainWindow.loadURL(`http://localhost:${LOCAL_SERVER_PORT}`);
    });
    
    localServer.on('error', (err) => {
      console.error('Server error:', err);
    });
  }
  
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('Failed to load:', errorCode, errorDescription);
  });
  
  mainWindow.webContents.on('did-finish-load', () => {
    console.log('Page finished loading');
  });
}

// Check if service is running on port
function isPortInUse(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => resolve(true));
    server.once('listening', () => {
      server.close();
      resolve(false);
    });
    server.listen(port);
  });
}

// Start Master process
function startMaster(customPythonPath = 'python') {
  if (masterProcess) {
    return Promise.resolve({ success: false, message: 'Master already running' });
  }

  return new Promise((resolve) => {
    console.log(`Backend path: ${BACKEND_PATH}`);
    console.log(`Backend exists: ${require('fs').existsSync(BACKEND_PATH)}`);
    console.log(`Custom Python path: ${customPythonPath}`);
    
    // Use custom Python path if provided, otherwise try to find Python
    let pythonCmd = customPythonPath;
    
    // If custom path is just 'python', try to find it in common locations
    if (pythonCmd === 'python' || pythonCmd === 'python3') {
      const pythonPaths = [
        'py',  // Python launcher - most reliable
        'python',
        'python3',
        'python.exe',
        path.join(process.env.ProgramFiles || '', 'Python311', 'python.exe'),
        path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python311', 'python.exe'),
        path.join(process.env.ProgramFiles || '', 'Python310', 'python.exe'),
        path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python310', 'python.exe')
      ];
      
      for (const pyPath of pythonPaths) {
        if (require('fs').existsSync(pyPath)) {
          pythonCmd = pyPath;
          console.log(`Found Python at: ${pythonCmd}`);
          break;
        }
      }
    }
    
    console.log(`Using Python: ${pythonCmd}`);
    
    masterProcess = spawn(pythonCmd, ['-m', 'backend.main'], {
      cwd: BACKEND_PATH,
      shell: false,
      env: { ...process.env, NODE_ROLE: 'MASTER' }
    });

    masterProcess.stdout.on('data', (data) => {
      console.log(`Master stdout: ${data}`);
      mainWindow?.webContents.send('master-log', data.toString());
    });

    masterProcess.stderr.on('data', (data) => {
      console.error(`Master stderr: ${data}`);
      mainWindow?.webContents.send('master-log', data.toString());
    });

    masterProcess.on('error', (error) => {
      console.error(`Master process error: ${error}`);
      resolve({ success: false, message: `Master error: ${error.message}` });
    });

    masterProcess.on('close', (code) => {
      console.log(`Master process exited with code ${code}`);
      masterProcess = null;
      mainWindow?.webContents.send('master-stopped', { code });
    });

    // Wait a bit and check if it started successfully
    setTimeout(async () => {
      const isRunning = await isPortInUse(MASTER_PORT);
      resolve({ success: isRunning, message: isRunning ? 'Master started' : 'Master failed to start' });
    }, 3000);
  });
}

// Start Worker process
function startWorker(workerIp) {
  if (workerProcess) {
    return Promise.resolve({ success: false, message: 'Worker already running' });
  }

  return new Promise((resolve) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    const env = { ...process.env, NODE_ROLE: 'WORKER', WORKER_HOST: workerIp };
    
    workerProcess = spawn(pythonCmd, ['-m', 'backend.main'], {
      cwd: BACKEND_PATH,
      shell: true,
      env
    });

    workerProcess.stdout.on('data', (data) => {
      console.log(`Worker stdout: ${data}`);
      mainWindow?.webContents.send('worker-log', data.toString());
    });

    workerProcess.stderr.on('data', (data) => {
      console.error(`Worker stderr: ${data}`);
      mainWindow?.webContents.send('worker-log', data.toString());
    });

    workerProcess.on('close', (code) => {
      console.log(`Worker process exited with code ${code}`);
      workerProcess = null;
      mainWindow?.webContents.send('worker-stopped', { code });
    });

    resolve({ success: true, message: 'Worker starting...' });
  });
}

// UDP Discovery for auto-linking (compatible with backend Python)
let localIpAddress = null;
let nodeId = null;

function getLocalIpAddress() {
  const interfaces = require('os').networkInterfaces();
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        return iface.address;
      }
    }
  }
  return '127.0.0.1';
}

function startDiscovery() {
  if (discoverySocket) {
    discoverySocket.close();
  }

  // Get local IP and generate node ID
  localIpAddress = getLocalIpAddress();
  nodeId = `master-${Date.now()}`;
  console.log(`Local IP address: ${localIpAddress}`);
  console.log(`Node ID: ${nodeId}`);

  discoverySocket = dgram.createSocket('udp4');
  
  discoverySocket.on('message', (msg, rinfo) => {
    try {
      const data = JSON.parse(msg.toString());
      
      // Check magic string (must match backend protocol)
      if (data.magic !== 'SYNAPSE_V2') {
        return;
      }
      
      // Ignore messages from ourselves
      if (data.node_id === nodeId) {
        console.log(`Ignoring message from self: ${rinfo.address}`);
        return;
      }
      
      // Only process WORKER responses (we are MASTER)
      if (data.role === 'WORKER') {
        console.log(`Worker discovered at ${rinfo.address}:${data.port}`);
        mainWindow?.webContents.send('worker-discovered', {
          ip: rinfo.address,
          port: data.port,
          role: data.role,
          node_id: data.node_id
        });
      }
    } catch (e) {
      console.error('Discovery parse error:', e);
    }
  });

  discoverySocket.bind(DISCOVERY_PORT, () => {
    discoverySocket.setBroadcast(true);
    console.log(`Discovery listening on port ${DISCOVERY_PORT}`);
  });
}

// Broadcast discovery message (compatible with backend Python)
function broadcastDiscovery() {
  if (!discoverySocket) return;
  
  const message = JSON.stringify({
    magic: 'SYNAPSE_V2',
    node_id: nodeId,
    role: 'MASTER',
    port: MASTER_PORT,
    timestamp: Date.now() / 1000
  });
  
  console.log(`Broadcasting discovery message from ${localIpAddress}`);
  discoverySocket.send(message, DISCOVERY_PORT, '255.255.255.255');
}

// Check connection status
async function checkConnectionStatus() {
  const masterRunning = await isPortInUse(MASTER_PORT);
  
  // Try to ping worker via API
  let workerConnected = false;
  let transferSpeed = 0;
  
  if (masterRunning) {
    try {
      const axios = require('axios');
      const response = await axios.get('http://localhost:8000/api/v1/system/health', { timeout: 2000 });
      if (response.data && response.data.worker_connected) {
        workerConnected = true;
        transferSpeed = response.data.transfer_speed || 0;
      }
    } catch (e) {
      // API not available
    }
  }
  
  return {
    master: masterRunning,
    worker: workerConnected,
    linked: masterRunning && workerConnected,
    transferSpeed
  };
}

// Scan local network for worker by checking common IP range
async function scanLocalNetworkForWorker() {
  const os = require('os');
  const interfaces = os.networkInterfaces();
  const localIp = getLocalIpAddress();
  
  if (!localIp || localIp === '127.0.0.1') {
    console.log('Cannot determine local IP for network scan');
    return null;
  }
  
  // Get subnet (e.g., 192.168.1 from 192.168.1.45)
  const ipParts = localIp.split('.');
  const subnet = `${ipParts[0]}.${ipParts[1]}.${ipParts[2]}`;
  
  console.log(`Scanning subnet ${subnet}.x for worker on port ${MASTER_PORT}...`);
  
  // Scan IPs in the subnet (limit to common range)
  const promises = [];
  for (let i = 1; i <= 254; i++) {
    if (i === parseInt(ipParts[3])) continue; // Skip our own IP
    
    const targetIp = `${subnet}.${i}`;
    promises.push(checkPortOnHost(targetIp, MASTER_PORT));
  }
  
  const results = await Promise.all(promises);
  
  for (let i = 0; i < results.length; i++) {
    if (results[i]) {
      const targetIp = `${subnet}.${i + 1}`;
      if (parseInt(ipParts[3]) !== i + 1) {
        console.log(`Worker found at ${targetIp}:${MASTER_PORT}`);
        return targetIp;
      }
    }
  }
  
  console.log('Worker not found in local network scan');
  return null;
}

// Find IP by MAC address using ARP
async function findIpByMacAddress(targetMac) {
  const { exec } = require('child_process');
  const os = require('os');
  const localIp = getLocalIpAddress();
  
  if (!localIp || localIp === '127.0.0.1') {
    console.log('Cannot determine local IP for MAC scan');
    return null;
  }
  
  // Normalize MAC address format (remove colons and dashes, convert to uppercase)
  const normalizedMac = targetMac.replace(/[:-]/g, '').toUpperCase();
  
  // Get subnet
  const ipParts = localIp.split('.');
  const subnet = `${ipParts[0]}.${ipParts[1]}.${ipParts[2]}`;
  
  console.log(`Scanning for MAC ${targetMac} in subnet ${subnet}.x...`);
  
  // Ping all IPs in subnet to populate ARP table
  const pingPromises = [];
  for (let i = 1; i <= 254; i++) {
    if (i === parseInt(ipParts[3])) continue;
    
    const targetIp = `${subnet}.${i}`;
    pingPromises.push(
      new Promise((resolve) => {
        exec(`ping -n 1 -w 100 ${targetIp}`, () => resolve());
      })
    );
  }
  
  await Promise.all(pingPromises);
  
  // Get ARP table
  return new Promise((resolve) => {
    exec('arp -a', (error, stdout) => {
      if (error) {
        console.error('Error getting ARP table:', error);
        resolve(null);
        return;
      }
      
      // Parse ARP table to find IP for the MAC
      const lines = stdout.split('\n');
      for (const line of lines) {
        // ARP table format: "  192.168.1.43           e0-0a-f6-9e-cb-01     dynamic"
        const match = line.match(/(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F-:]+)/);
        if (match) {
          const ip = match[1];
          const mac = match[2].replace(/[:-]/g, '').toUpperCase();
          
          if (mac === normalizedMac) {
            console.log(`Found IP ${ip} for MAC ${targetMac}`);
            resolve(ip);
            return;
          }
        }
      }
      
      console.log(`MAC ${targetMac} not found in ARP table`);
      resolve(null);
    });
  });
}

// Check if a specific host:port is open
function checkPortOnHost(host, port) {
  return new Promise((resolve) => {
    const socket = require('net').createConnection(port, host);
    
    socket.setTimeout(1000); // 1 second timeout
    
    socket.on('connect', () => {
      socket.destroy();
      resolve(true);
    });
    
    socket.on('timeout', () => {
      socket.destroy();
      resolve(false);
    });
    
    socket.on('error', () => {
      resolve(false);
    });
  });
}

// Start Worker remotely - disabled in packaged environment
async function startWorkerRemotely(workerIp, username, password, networkPath) {
  // Remote start is not supported in packaged environment
  // User must start Worker manually via RDP
  return { 
    success: false, 
    message: 'Arranque remoto no disponible en versión empaquetada. Usa RDP para iniciar el Worker manualmente.' 
  };
}

// IPC Handlers
ipcMain.handle('check-connection', async () => {
  return await checkConnectionStatus();
});

ipcMain.handle('start-master', async (event, pythonPath) => {
  return await startMaster(pythonPath);
});

ipcMain.handle('start-worker', async (event, workerIp) => {
  return await startWorker(workerIp);
});

ipcMain.handle('start-worker-remote', async (event, workerIp, username, password, networkPath) => {
  return await startWorkerRemotely(workerIp, username, password, networkPath);
});

ipcMain.handle('stop-master', async () => {
  if (masterProcess) {
    masterProcess.kill();
    masterProcess = null;
    return { success: true, message: 'Master stopped' };
  }
  return { success: false, message: 'Master not running' };
});

ipcMain.handle('stop-worker', async () => {
  if (workerProcess) {
    workerProcess.kill();
    workerProcess = null;
    return { success: true, message: 'Worker stopped' };
  }
  return { success: false, message: 'Worker not running' };
});

ipcMain.handle('start-discovery', () => {
  startDiscovery();
  return { success: true };
});

ipcMain.handle('broadcast-discovery', () => {
  broadcastDiscovery();
  return { success: true };
});

ipcMain.handle('scan-network', async () => {
  const workerIp = await scanLocalNetworkForWorker();
  if (workerIp) {
    mainWindow?.webContents.send('worker-discovered', {
      ip: workerIp,
      port: MASTER_PORT,
      role: 'WORKER',
      node_id: 'scanned'
    });
    return { success: true, ip: workerIp };
  }
  return { success: false, message: 'Worker not found in network scan' };
});

ipcMain.handle('find-by-mac', async (event, macAddress) => {
  const workerIp = await findIpByMacAddress(macAddress);
  if (workerIp) {
    mainWindow?.webContents.send('worker-discovered', {
      ip: workerIp,
      port: MASTER_PORT,
      role: 'WORKER',
      node_id: 'mac-discovered'
    });
    return { success: true, ip: workerIp };
  }
  return { success: false, message: `MAC ${macAddress} not found in network` };
});

ipcMain.handle('open-external', (event, url) => {
  shell.openExternal(url);
});

ipcMain.handle('create-rdp-file', (event, rdpPath, rdpContent) => {
  const fs = require('fs');
  try {
    fs.writeFileSync(rdpPath, rdpContent, 'utf-8');
    return { success: true, message: 'RDP file created' };
  } catch (error) {
    return { success: false, message: error.message };
  }
});

ipcMain.handle('open-rdp', (event, rdpPath) => {
  const { spawn } = require('child_process');
  try {
    spawn('mstsc.exe', [rdpPath], { detached: true });
    return { success: true, message: 'RDP opened' };
  } catch (error) {
    return { success: false, message: error.message };
  }
});

// App lifecycle
app.whenReady().then(() => {
  createWindow();
  startDiscovery();
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (localServer) {
    localServer.close();
  }
  if (masterProcess) {
    masterProcess.kill();
  }
  if (workerProcess) {
    workerProcess.kill();
  }
  if (discoverySocket) {
    discoverySocket.close();
  }
  
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
