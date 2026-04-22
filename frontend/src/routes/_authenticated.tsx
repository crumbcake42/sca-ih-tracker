import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { useAuthStore } from "@/auth/store";
import { currentUserOptions } from "@/auth/api";
import { queryClient } from "@/api/queryClient";
import { AppShell } from "@/components/AppShell";

export const Route = createFileRoute("/_authenticated")({
  beforeLoad: async () => {
    if (typeof window === "undefined") return;
    try {
      await queryClient.ensureQueryData(currentUserOptions());
    } catch {
      useAuthStore.getState().clearAuth();
      throw redirect({ to: "/login" });
    }
  },
  component: AuthenticatedLayout,
});

function AuthenticatedLayout() {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}
