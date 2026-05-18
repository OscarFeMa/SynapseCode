import React from 'react'
import ReactDOM from 'react-dom/client'
import { Toaster } from 'sonner'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
    <Toaster
      position="bottom-right"
      toastOptions={{
        style: {
          background: '#FFFFFF',
          border: '1px solid rgba(0,0,0,0.08)',
          color: '#161616',
          boxShadow: '0 1px 2px rgba(0,0,0,0.03), 0 8px 24px rgba(0,0,0,0.04)',
          borderRadius: '8px',
          fontSize: '14px',
        },
        success: {
          style: {
            borderLeft: '3px solid #4A7C59',
          },
        },
        error: {
          style: {
            borderLeft: '3px solid #8B3A3A',
          },
        },
        info: {
          style: {
            borderLeft: '3px solid #23403B',
          },
        },
      }}
    />
  </React.StrictMode>,
)
