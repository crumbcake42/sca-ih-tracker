import { Link, useRouterState } from "@tanstack/react-router";
import { CaretLeftIcon, CaretRightIcon } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";
import { useAdminShellStore } from "@/lib/admin-shell-state";
import { ADMIN_NAV_ITEMS } from "./nav-items";
import type { AdminNavItem } from "./nav-items";

function itemIsActive(pathname: string, to: string): boolean {
  if (to === "/admin") return pathname === "/admin";
  return pathname.startsWith(to);
}

function NavItemContent({
  item,
  active,
  collapsed,
}: {
  item: AdminNavItem;
  active: boolean;
  collapsed: boolean;
}) {
  return (
    <span
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
        active
          ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
          : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
        item.disabled && "pointer-events-none opacity-40",
        collapsed && "justify-center px-2",
      )}
      title={collapsed ? item.label : undefined}
    >
      <item.Icon size={18} />
      {!collapsed && <span>{item.label}</span>}
    </span>
  );
}

export function AdminSidebar() {
  const collapsed = useAdminShellStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useAdminShellStore((s) => s.toggleSidebar);
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <aside
      className={cn(
        "flex h-full flex-shrink-0 flex-col border-r bg-sidebar transition-[width] duration-200",
        collapsed ? "w-16" : "w-60",
      )}
    >
      <div
        className={cn(
          "flex h-14 items-center border-b border-sidebar-border px-4",
          collapsed && "justify-center",
        )}
      >
        {collapsed ? (
          <span className="text-sm font-bold leading-none">S</span>
        ) : (
          <span className="text-sm font-semibold tracking-tight">
            SCA IH Tracker
          </span>
        )}
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
        {ADMIN_NAV_ITEMS.map((item) => {
          if (item.disabled) {
            return (
              <div key={item.label}>
                <NavItemContent
                  item={item}
                  active={false}
                  collapsed={collapsed}
                />
              </div>
            );
          }
          return (
            <Link key={item.to} to={item.to as never}>
              <NavItemContent
                item={item}
                active={itemIsActive(pathname, item.to)}
                collapsed={collapsed}
              />
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-sidebar-border p-2">
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand sidebar" : undefined}
          className={cn(
            "flex w-full items-center rounded-md p-2 text-xs",
            "text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground",
            "transition-colors",
            collapsed ? "justify-center" : "gap-2",
          )}
        >
          {collapsed ? (
            <CaretRightIcon size={16} />
          ) : (
            <>
              <CaretLeftIcon size={16} />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
