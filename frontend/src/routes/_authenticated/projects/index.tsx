import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";

import { getProjectsProjectsGetOptions } from "../../../api/generated/@tanstack/react-query.gen";
import type { Project } from "../../../api/generated/types.gen";
import { DataTable } from "@/components/DataTable";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { useUrlSearch } from "@/hooks/useUrlSearch";
import { useUrlPagination } from "@/hooks/useUrlPagination";

export const Route = createFileRoute("/_authenticated/projects/")({
  validateSearch: (
    search: Record<string, unknown>,
  ): { search?: string; page?: number; pageSize?: number } => ({
    search: typeof search.search === "string" ? search.search : undefined,
    page: typeof search.page === "number" ? search.page : undefined,
    pageSize: typeof search.pageSize === "number" ? search.pageSize : undefined,
  }),
  component: ProjectsPage,
});

const columns: ColumnDef<Project>[] = [
  {
    accessorKey: "project_number",
    header: "Project #",
    cell: ({ getValue }) => (
      <span className="font-mono">{getValue<string>()}</span>
    ),
  },
  {
    accessorKey: "name",
    header: "Name",
  },
  {
    accessorKey: "school_ids",
    header: "Schools",
    cell: ({ getValue }) => getValue<number[] | undefined>()?.length ?? 0,
  },
];

function ProjectsPage() {
  const [nameSearch, setNameSearch] = useUrlSearch("search");
  const { pagination, onPaginationChange } = useUrlPagination();

  const {
    data: projects,
    isLoading,
    error,
  } = useQuery(
    getProjectsProjectsGetOptions({
      query: { name_search: nameSearch || undefined },
    }),
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <Input
          placeholder="Search projects…"
          value={nameSearch}
          onChange={(e) => setNameSearch(e.target.value)}
          className="w-56"
        />
      </div>

      <Card>
        <CardContent className="p-0">
          <DataTable
            columns={columns}
            data={projects ?? []}
            pagination={pagination}
            onPaginationChange={onPaginationChange}
            pageCount={1}
            isLoading={isLoading}
            error={error}
            emptyMessage="No projects found."
          />
        </CardContent>
      </Card>
    </div>
  );
}
