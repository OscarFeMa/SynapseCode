import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  MessageSquare,
  PlusCircle,
  BarChart3,
  Scale,
  Cpu,
  History,
  Database,
  Settings,
  ChevronLeft,
  ChevronRight,
  Search,
} from 'lucide-react'

const navGroups = [
  {
    label: 'Principal',
    items: [
      { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
      { icon: MessageSquare, label: 'Debates', path: '/debates' },
      { icon: PlusCircle, label: 'Nuevo Debate', path: '/debates/new' },
    ],
  },
  {
    label: 'Sistema',
    items: [
      { icon: BarChart3, label: 'Monitor', path: '/monitor' },
      { icon: Scale, label: 'Tribunal', path: '/tribunal' },
      { icon: Cpu, label: 'Modelos', path: '/models' },
      { icon: Database, label: 'Cache', path: '/cache' },
    ],
  },
  {
    label: 'General',
    items: [
      { icon: History, label: 'Historico', path: '/history' },
      { icon: Settings, label: 'Ajustes', path: '/settings' },
    ],
  },
]

export function Sidebar({ onOpenCommandPalette }) {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()

  return (
    <aside
      className={`fixed left-0 top-0 h-screen bg-slate-900 border-r border-slate-800 z-50 transition-all duration-300 flex flex-col ${
        collapsed ? 'w-16' : 'w-56'
      }`}
    >
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-slate-800">
        <div className="w-8 h-8 bg-amber-500 rounded-lg flex items-center justify-center flex-shrink-0">
          <span className="text-slate-900 font-bold text-sm">S</span>
        </div>
        {!collapsed && (
          <div className="ml-3 overflow-hidden">
            <div className="text-white font-semibold text-sm whitespace-nowrap">SynapseCode</div>
            <div className="text-slate-500 text-[10px] whitespace-nowrap">v3.0</div>
          </div>
        )}
      </div>

      {/* Search button */}
      {!collapsed && (
        <button
          onClick={onOpenCommandPalette}
          className="mx-3 mt-3 flex items-center gap-2 px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-xs text-slate-500 hover:text-white hover:border-slate-600 transition-colors"
        >
          <Search className="w-3.5 h-3.5" />
          <span>Buscar...</span>
          <kbd className="ml-auto text-[10px] bg-slate-700 px-1.5 py-0.5 rounded font-mono">Ctrl+K</kbd>
        </button>
      )}

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        {navGroups.map((group) => (
          <div key={group.label} className="mb-4">
            {!collapsed && (
              <div className="px-4 mb-1 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                {group.label}
              </div>
            )}
            {group.items.map((item) => {
              const isActive = location.pathname === item.path
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-2 mx-2 rounded-lg text-sm transition-all ${
                    isActive
                      ? 'bg-amber-500/10 text-amber-500 border-l-2 border-amber-500'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800'
                  }`}
                  title={collapsed ? item.label : undefined}
                >
                  <item.icon className="w-4 h-4 flex-shrink-0" />
                  {!collapsed && <span className="whitespace-nowrap">{item.label}</span>}
                </Link>
              )
            })}
          </div>
        ))}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center h-10 border-t border-slate-800 text-slate-400 hover:text-white transition-colors"
      >
        {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>
    </aside>
  )
}
