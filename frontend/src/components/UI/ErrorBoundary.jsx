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
        <div className="flex flex-col items-center justify-center min-h-[300px] bg-white border border-[#8B3A3A]/15 rounded-lg p-8 shadow-card">
          <AlertTriangle className="w-10 h-10 text-[#8B3A3A] mb-4" />
          <h3 className="text-lg font-serif text-[#161616] mb-2">Algo salio mal</h3>
          <p className="text-sm text-[#5C5C5C] mb-4 text-center max-w-md">
            {this.state.error?.message || 'Error inesperado en la interfaz'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-[rgba(0,0,0,0.08)] rounded text-sm text-[#161616] hover:bg-[#F5F3EE] transition-colors"
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
