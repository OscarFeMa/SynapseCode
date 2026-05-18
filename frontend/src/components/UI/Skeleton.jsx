export function Skeleton({ className = '' }) {
  return (
    <div
      className={`animate-pulse bg-[#ECE9E2] rounded ${className}`}
    />
  )
}

export function CardSkeleton() {
  return (
    <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card space-y-3">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-8 w-16" />
      <Skeleton className="h-3 w-full" />
    </div>
  )
}

export function TableSkeleton({ rows = 5 }) {
  return (
    <div className="bg-white border border-[rgba(0,0,0,0.08)] rounded-lg p-5 shadow-card space-y-4">
      <Skeleton className="h-4 w-32" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4">
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-16 hidden lg:block" />
          <Skeleton className="h-4 w-24 hidden md:block" />
        </div>
      ))}
    </div>
  )
}

export function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-4 w-72" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
      <TableSkeleton rows={5} />
    </div>
  )
}
