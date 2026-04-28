import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import type {
  ColumnDef,
  PaginationState,
  OnChangeFn,
} from "@tanstack/react-table";
import type { Project } from "@/api/generated/types.gen";
import { listProjectsOptions } from "@/features/projects/api/projects";
import { DataTable } from "@/components/DataTable";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";

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
    cell: ({ row }) => (
      <Link
        to="/projects/$projectId"
        params={{ projectId: String(row.original.id) }}
        className="text-primary underline-offset-2 hover:underline"
      >
        {row.original.name}
      </Link>
    ),
  },
  {
    accessorKey: "school_ids",
    header: "Schools",
    cell: ({ getValue }) => getValue<number[] | undefined>()?.length ?? 0,
  },
];

interface Props {
  search: string;
  onSearchChange: (value: string) => void;
  pagination: PaginationState;
  onPaginationChange: OnChangeFn<PaginationState>;
}

export function ProjectList({
  search,
  onSearchChange,
  pagination,
  onPaginationChange,
}: Props) {
  const {
    data: projects,
    isLoading,
    error,
  } = useQuery(
    listProjectsOptions({
      query: { name_search: search || undefined },
    }),
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <Input
          placeholder="Search projects…"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
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
