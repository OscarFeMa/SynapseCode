export function TribunalPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Tribunal</h1>
        <p className="text-sm text-slate-400 mt-1">Panel de magistrados y veredictos</p>
      </div>
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
        <p className="text-slate-500">Proximamente</p>
      </div>
    </div>
  )
}

export function HistoryPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Historico</h1>
        <p className="text-sm text-slate-400 mt-1">Historial de debates con graficas de tendencias</p>
      </div>
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
        <p className="text-slate-500">Fase 9 - En desarrollo</p>
      </div>
    </div>
  )
}
