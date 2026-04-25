import { createFileRoute } from "@tanstack/react-router";
import { ContractorListPage } from "@/pages/admin/contractors";

export const Route = createFileRoute("/_authenticated/admin/contractors/")({
  validateSearch: (
    search: Record<string, unknown>,
  ): { search?: string; page?: number; pageSize?: number } => ({
    search: typeof search.search === "string" ? search.search : undefined,
    page: typeof search.page === "number" ? search.page : undefined,
    pageSize: typeof search.pageSize === "number" ? search.pageSize : undefined,
  }),
  component: ContractorListPage,
});
