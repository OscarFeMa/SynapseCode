import { useState, useEffect, useCallback } from 'react'
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
  Menu,
  X,
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
  const [mobileOpen, setMobileOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const location = useLocation()

  const checkMobile = useCallback(() => {
    const mobile = window.innerWidth < 768
    setIsMobile(mobile)
    if (mobile) setCollapsed(true)
  }, [])

  useEffect(() => {
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [checkMobile])

  // Close mobile sidebar on navigation
  useEffect(() => {
    if (isMobile) setMobileOpen(false)
  }, [location.pathname, isMobile])

  const visible = isMobile ? mobileOpen : !collapsed

  return (
    <>
      {/* Mobile hamburger */}
      {isMobile && !mobileOpen && (
        <button
          onClick={() => setMobileOpen(true)}
          className="fixed top-3 left-3 z-50 w-9 h-9 flex items-center justify-center bg-white border border-[rgba(0,0,0,0.08)] rounded shadow-sm text-[#5C5C5C] hover:text-[#161616] transition-colors"
        >
          <Menu className="w-4 h-4" />
        </button>
      )}

      {/* Mobile overlay */}
      {isMobile && mobileOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`
          bg-white border-r border-[rgba(0,0,0,0.08)] flex flex-col
          transition-all duration-300
          ${isMobile
            ? `fixed top-0 left-0 h-screen z-50 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`
            : `fixed left-0 top-0 h-screen z-50 ${collapsed ? 'w-16' : 'w-56'}`
          }
        `}
        style={isMobile ? { width: '220px' } : undefined}
      >
        {/* Header */}
        <div className="h-14 flex items-center px-4 border-b border-[rgba(0,0,0,0.08)]">
          <div className="w-8 h-8 bg-[#23403B] rounded flex items-center justify-center flex-shrink-0">
            <span className="text-[#F5F3EE] font-serif font-bold text-sm">S</span>
          </div>
          {visible && (
            <>
              <div className="ml-3 overflow-hidden flex-1">
                <div className="text-[#161616] font-serif text-base leading-tight">SynapseCode</div>
                <div className="text-[#8A8780] text-[10px] tracking-wider uppercase">v3.0</div>
              </div>
              {isMobile && (
                <button onClick={() => setMobileOpen(false)} className="p-1 text-[#8A8780] hover:text-[#161616]">
                  <X className="w-4 h-4" />
                </button>
              )}
            </>
          )}
        </div>

        {/* Search */}
        {visible && (
          <button
            onClick={onOpenCommandPalette}
            className="mx-3 mt-3 flex items-center gap-2 px-3 py-2 bg-[#F5F3EE] border border-[rgba(0,0,0,0.06)] rounded text-xs text-[#5C5C5C] hover:text-[#161616] hover:border-[rgba(0,0,0,0.12)] transition-colors"
          >
            <Search className="w-3.5 h-3.5" />
            <span>Buscar...</span>
            <kbd className="ml-auto text-[10px] bg-white px-1.5 py-0.5 rounded font-mono text-[#8A8780]">Ctrl+K</kbd>
          </button>
        )}

        {/* Navigation */}
        <nav className="flex-1 py-4 overflow-y-auto">
          {navGroups.map((group) => (
            <div key={group.label} className="mb-5">
              {visible && (
                <div className="px-4 mb-1.5 text-[10px] font-semibold text-[#8A8780] uppercase tracking-widest">
                  {group.label}
                </div>
              )}
              {group.items.map((item) => {
                const isActive = location.pathname === item.path
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center gap-3 px-4 py-2 mx-2 rounded text-sm transition-all ${
                      isActive
                        ? 'bg-[#23403B]/[0.06] text-[#23403B] font-medium'
                        : 'text-[#5C5C5C] hover:text-[#161616] hover:bg-[#F5F3EE]'
                    }`}
                    title={!visible ? item.label : undefined}
                  >
                    <item.icon className="w-4 h-4 flex-shrink-0" />
                    {visible && <span className="whitespace-nowrap">{item.label}</span>}
                  </Link>
                )
              })}
            </div>
          ))}
        </nav>

        {/* Desktop collapse toggle */}
        {!isMobile && (
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="flex items-center justify-center h-10 border-t border-[rgba(0,0,0,0.08)] text-[#8A8780] hover:text-[#161616] transition-colors"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        )}
      </aside>
    </>
  )
}
