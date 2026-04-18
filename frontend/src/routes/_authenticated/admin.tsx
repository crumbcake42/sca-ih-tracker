import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'
import { useAuthStore } from '../../auth/store'

export const Route = createFileRoute('/_authenticated/admin')({
  beforeLoad: () => {
    if (typeof window === 'undefined') return
    if (!useAuthStore.getState().user?.is_admin) {
      throw redirect({ to: '/projects' })
    }
  },
  component: AdminLayout,
})

function AdminLayout() {
  return <Outlet />
}
