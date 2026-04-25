import { createFileRoute } from "@tanstack/react-router";
import { prefetchContractor } from "@/pages/admin/contractors/loader";
import { ContractorDetailPage } from "@/pages/admin/contractors/detail";

export const Route = createFileRoute(
  "/_authenticated/admin/contractors/$contractorId",
)({
  loader: ({ params }) => prefetchContractor(Number(params.contractorId)),
  component: ContractorDetailPage,
});
