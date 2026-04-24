import { createFileRoute, redirect } from "@tanstack/react-router";
import { useAuthStore } from "@/auth/store";
import { AdminLayout } from "@/pages/admin/layout";

export const Route = createFileRoute("/_authenticated/admin")({
  beforeLoad: () => {
    if (typeof window === "undefined") return;
    const user = useAuthStore.getState().user;
    if (!user?.role) {
      throw redirect({ to: "/login" });
    } else if (user.role.name !== "admin" && user.role.name !== "superadmin") {
      throw redirect({ to: "/" });
    }
  },
  component: AdminLayout,
});
