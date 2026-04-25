import { createFileRoute } from "@tanstack/react-router";
import { prefetchWaCode } from "@/pages/admin/wa-codes/loader";
import { WaCodeDetailPage } from "@/pages/admin/wa-codes/detail";

export const Route = createFileRoute(
  "/_authenticated/admin/wa-codes/$waCodeId",
)({
  loader: ({ params }) => prefetchWaCode(Number(params.waCodeId)),
  component: WaCodeDetailPage,
});
