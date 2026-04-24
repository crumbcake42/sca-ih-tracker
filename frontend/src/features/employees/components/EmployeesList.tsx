import { useQuery } from "@tanstack/react-query";
import type {
  ColumnDef,
  PaginationState,
  OnChangeFn,
} from "@tanstack/react-table";
import { PlusIcon } from "@phosphor-icons/react";
import type { Employee } from "@/api/generated/types.gen";
import { listEmployeesOptions } from "@/features/employees/api/employees";
import { DataTable } from "@/components/DataTable";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const columns: ColumnDef<Employee>[] = [
  {
    id: "name",
    header: "Name",
    cell: ({ row }) => {
      const { first_name, last_name, display_name } = row.original;
      return display_name ?? `${first_name} ${last_name}`;
    },
  },
  {
    accessorKey: "title",
    header: "Title",
    cell: ({ getValue }) => getValue<string | null>() ?? "—",
  },
  {
    accessorKey: "email",
    header: "Email",
    cell: ({ getValue }) => getValue<string | null>() ?? "—",
  },
  {
    accessorKey: "adp_id",
    header: "ADP ID",
    cell: ({ getValue }) => {
      const v = getValue<string | null>();
      return v ? <span className="font-mono text-xs">{v}</span> : "—";
    },
  },
];

interface Props {
  search: string;
  onSearchChange: (value: string) => void;
  pagination: PaginationState;
  onPaginationChange: OnChangeFn<PaginationState>;
  onRowClick: (employee: Employee) => void;
  onAddClick: () => void;
}

export function EmployeesList({
  search,
  onSearchChange,
  pagination,
  onPaginationChange,
  onRowClick,
  onAddClick,
}: Props) {
  const { data, isLoading, error } = useQuery(
    listEmployeesOptions({
      query: {
        search: search || undefined,
        skip: pagination.pageIndex * pagination.pageSize,
        limit: pagination.pageSize,
      },
    }),
  );

  const pageCount = data ? Math.ceil(data.total / data.limit) : 1;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Employees</h1>
        <div className="flex items-center gap-2">
          <Input
            placeholder="Search employees…"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-56"
          />
          <Button size="sm" onClick={onAddClick}>
            <PlusIcon size={15} />
            Add employee
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <DataTable
            columns={columns}
            data={data?.items ?? []}
            pagination={pagination}
            onPaginationChange={onPaginationChange}
            pageCount={pageCount}
            isLoading={isLoading}
            error={error}
            emptyMessage="No employees found."
            onRowClick={onRowClick}
          />
        </CardContent>
      </Card>
    </div>
  );
}
