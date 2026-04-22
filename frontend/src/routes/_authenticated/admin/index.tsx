import { createFileRoute } from "@tanstack/react-router";
import { AdminOverviewPage } from "@/pages/admin";

export const Route = createFileRoute("/_authenticated/admin/")({
  component: AdminOverviewPage,
});
