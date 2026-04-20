import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'
import { useAuthStore } from '../auth/store'
import { AppShell } from '@/components/AppShell'

export const Route = createFileRoute('/_authenticated')({
  beforeLoad: () => {
    if (typeof window === 'undefined') return
    const state = useAuthStore.getState()
    console.log({ state })
    if (!state.token) {
      throw redirect({ to: '/login' })
    }
  },
  component: AuthenticatedLayout,
})

function AuthenticatedLayout() {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  )
}
