import { createFileRoute, redirect } from "@tanstack/react-router";
import { useAuthStore } from "@/auth/store";

export const Route = createFileRoute("/_authenticated/")({
  beforeLoad: () => {
    const user = useAuthStore.getState().user;
    if (!user) throw redirect({ to: "/login" });
    const role = user.role.name;
    if (role === "admin" || role === "superadmin") {
      throw redirect({ to: "/admin" });
    }
    throw redirect({ to: "/dashboard" });
  },
});
