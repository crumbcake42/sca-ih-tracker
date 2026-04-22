import { createFileRoute, redirect } from "@tanstack/react-router";
import { z } from "zod";
import { useAuthStore } from "@/auth/store";
import { LoginPage } from "@/pages/login";

const searchSchema = z.object({
  redirect: z.string().optional(),
});

export const Route = createFileRoute("/login")({
  validateSearch: searchSchema,
  beforeLoad: () => {
    if (typeof window === "undefined") return;
    if (useAuthStore.getState().token) {
      throw redirect({ to: "/" });
    }
  },
  component: LoginPage,
});
