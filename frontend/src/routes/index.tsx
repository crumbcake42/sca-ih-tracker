import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { Button } from '#/components/ui/button'
import { Badge } from '#/components/ui/badge'

export const Route = createFileRoute('/')({
  component: SmokeTestPage,
})

function SmokeTestPage() {
  const apiBase =
    typeof import.meta !== 'undefined'
      ? (import.meta.env?.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000')
      : 'http://127.0.0.1:8000'

  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ['smoke-test'],
    queryFn: async () => {
      const res = await fetch(`${apiBase}/`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return res.json()
    },
    retry: false,
  })

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <div className="flex flex-col items-center gap-2 text-center">
        <h1 className="text-2xl font-semibold">SCA IH Tracker</h1>
        <p className="text-muted-foreground text-sm">Session 0.1 smoke test</p>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-sm font-medium">Backend</span>
        {isLoading && <Badge variant="secondary">checking…</Badge>}
        {error && <Badge variant="destructive">unreachable</Badge>}
        {data && <Badge className="bg-green-600 text-white">connected</Badge>}
      </div>

      {data && (
        <pre className="bg-muted max-w-sm overflow-auto rounded p-3 text-xs">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}

      {error && (
        <p className="text-destructive max-w-sm text-center text-xs">
          {String(error)} — is the backend running at {apiBase}?
        </p>
      )}

      <Button variant="outline" size="sm" onClick={() => refetch()}>
        Retry
      </Button>
    </div>
  )
}
