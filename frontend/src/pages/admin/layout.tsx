import { Outlet } from "@tanstack/react-router";
import { AdminShell } from "./components/AdminShell";

export function AdminLayout() {
  return (
    <AdminShell>
      <Outlet />
    </AdminShell>
  );
}
