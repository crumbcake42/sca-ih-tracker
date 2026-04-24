import type { ReactNode } from "react";
import { useEffect } from "react";
import { AdminSidebar } from "./AdminSidebar";
import { AdminTopBar } from "./AdminTopBar";
import { useAdminShellStore } from "@/lib/admin-shell-state";

/** Two-column admin layout: collapsible sidebar + stacked top-bar/content. */
export function AdminShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <AdminSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <AdminTopBar />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}

/** Injects a page title into the AdminTopBar. Renders nothing. */
function Title({ children }: { children: ReactNode }) {
  const setPageTitle = useAdminShellStore((s) => s.setPageTitle);
  useEffect(() => {
    setPageTitle(children);
    return () => setPageTitle(null);
  }, [children, setPageTitle]);
  return null;
}

/** Injects primary action buttons into the AdminTopBar. Renders nothing. */
function Actions({ children }: { children: ReactNode }) {
  const setPageActions = useAdminShellStore((s) => s.setPageActions);
  useEffect(() => {
    setPageActions(children);
    return () => setPageActions(null);
  }, [children, setPageActions]);
  return null;
}

AdminShell.Title = Title;
AdminShell.Actions = Actions;
