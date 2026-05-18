import React from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[300px] bg-slate-900 border border-red-500/20 rounded-xl p-8">
          <AlertTriangle className="w-10 h-10 text-red-400 mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">Algo salio mal</h3>
          <p className="text-sm text-slate-400 mb-4 text-center max-w-md">
            {this.state.error?.message || 'Error inesperado en la interfaz'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white hover:bg-slate-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Reintentar
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
