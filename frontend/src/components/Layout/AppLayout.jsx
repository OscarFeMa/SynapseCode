import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'

export function AppLayout({ children }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <Sidebar />
      <div className="ml-56 min-h-screen flex flex-col transition-all duration-300">
        <TopBar />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  )
}
