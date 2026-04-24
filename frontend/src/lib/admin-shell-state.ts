import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ReactNode } from "react";

interface AdminShellState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  pageTitle: ReactNode;
  setPageTitle: (title: ReactNode) => void;
  pageActions: ReactNode;
  setPageActions: (actions: ReactNode) => void;
}

export const useAdminShellStore = create<AdminShellState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      toggleSidebar: () =>
        set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      pageTitle: null,
      setPageTitle: (pageTitle) => set({ pageTitle }),
      pageActions: null,
      setPageActions: (pageActions) => set({ pageActions }),
    }),
    {
      name: "admin-shell",
      partialize: (s) => ({ sidebarCollapsed: s.sidebarCollapsed }),
    },
  ),
);
