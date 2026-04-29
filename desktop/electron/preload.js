const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Connection status
  checkConnection: () => ipcRenderer.invoke('check-connection'),
  
  // Process control
  startMaster: () => ipcRenderer.invoke('start-master'),
  startWorker: (workerIp) => ipcRenderer.invoke('start-worker', workerIp),
  startWorkerRemote: (workerIp, username, password, networkPath) => 
    ipcRenderer.invoke('start-worker-remote', workerIp, username, password, networkPath),
  stopMaster: () => ipcRenderer.invoke('stop-master'),
  stopWorker: () => ipcRenderer.invoke('stop-worker'),
  
  // Discovery
  startDiscovery: () => ipcRenderer.invoke('start-discovery'),
  broadcastDiscovery: () => ipcRenderer.invoke('broadcast-discovery'),
  scanNetwork: () => ipcRenderer.invoke('scan-network'),
  findByMac: (macAddress) => ipcRenderer.invoke('find-by-mac', macAddress),
  
  // External links
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
  openRDP: (rdpPath) => ipcRenderer.invoke('open-rdp', rdpPath),
  createRDPFile: (rdpPath, rdpContent) => ipcRenderer.invoke('create-rdp-file', rdpPath, rdpContent),
  
  // Event listeners
  onMasterLog: (callback) => ipcRenderer.on('master-log', (event, data) => callback(data)),
  onWorkerLog: (callback) => ipcRenderer.on('worker-log', (event, data) => callback(data)),
  onWorkerDiscovered: (callback) => ipcRenderer.on('worker-discovered', (event, data) => callback(data)),
  onMasterStopped: (callback) => ipcRenderer.on('master-stopped', (event, data) => callback(data)),
  onWorkerStopped: (callback) => ipcRenderer.on('worker-stopped', (event, data) => callback(data)),
  
  // Remove listeners
  removeAllListeners: () => ipcRenderer.removeAllListeners()
});
