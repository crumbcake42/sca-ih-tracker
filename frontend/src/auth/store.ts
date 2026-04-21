import { create } from "zustand";
import { persist } from "zustand/middleware";
import { client } from "@/api/generated/client.gen";
import { setTokenGetter } from "@/api/client";
import type { User } from "@/api/generated/types.gen";

interface AuthState {
  user: User | null;
  token: string | null;
  setAuth: (token: string, user: User) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      setAuth: (token, user) => set({ token, user }),
      clearAuth: () => set({ token: null, user: null }),
    }),
    {
      name: "auth",
      partialize: (state) => ({ token: state.token, user: state.user }),
    },
  ),
);

client.setConfig({ auth: () => useAuthStore.getState().token ?? undefined });
setTokenGetter(() => useAuthStore.getState().token);

client.interceptors.response.use((response) => {
  if (response.status === 401) {
    useAuthStore.getState().clearAuth();
  }
  return response;
});
