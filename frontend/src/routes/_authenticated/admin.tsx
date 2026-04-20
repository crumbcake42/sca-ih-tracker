import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'
import { useAuthStore } from '../../auth/store'

export const Route = createFileRoute('/_authenticated/admin')({
  beforeLoad: () => {
    if (typeof window === 'undefined') return
    const user = useAuthStore.getState().user
    if (!user?.role) {
      throw redirect({ to: '/login' })
    } else if (user.role.name !== 'admin') {
      throw redirect({ to: '/' })
    }
  },
  component: AdminLayout,
})

function AdminLayout() {
  return <Outlet />
}
