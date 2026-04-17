import { createFileRoute, redirect } from '@tanstack/react-router'
import { useAuthStore } from '../auth/store'
import { AppShell } from '../components/AppShell'

export const Route = createFileRoute('/')({
  beforeLoad: () => {
    if (typeof window === 'undefined') return
    if (!useAuthStore.getState().token) {
      throw redirect({ to: '/login' })
    }
  },
  component: HomePage,
})

function HomePage() {
  return (
    <AppShell>
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <p className="text-muted-foreground text-sm">Project list coming in Session 1.x.</p>
      </div>
    </AppShell>
  )
}
