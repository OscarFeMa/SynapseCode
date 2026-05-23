import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { CommandPalette, useCommandPalette } from '../UI/CommandPalette'
import { ErrorBoundary } from '../UI/ErrorBoundary'

export function AppLayout({ children }) {
  const { isOpen, open, close } = useCommandPalette()

  return (
    <div className="min-h-screen bg-[#F5F3EE] text-[#161616]">
      <Sidebar onOpenCommandPalette={open} />
      <div className="md:ml-56 min-h-screen flex flex-col transition-all duration-300">
        <TopBar onOpenCommandPalette={open} />
        <main className="flex-1 p-6">
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </div>
      <CommandPalette isOpen={isOpen} onClose={close} />
    </div>
  )
}
