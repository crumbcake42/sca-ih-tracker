import { createFileRoute } from "@tanstack/react-router";
import { prefetchHygienist } from "@/pages/admin/hygienists/loader";
import { HygienistDetailPage } from "@/pages/admin/hygienists/detail";

export const Route = createFileRoute(
  "/_authenticated/admin/hygienists/$hygienistId",
)({
  loader: ({ params }) => prefetchHygienist(Number(params.hygienistId)),
  component: HygienistDetailPage,
});
