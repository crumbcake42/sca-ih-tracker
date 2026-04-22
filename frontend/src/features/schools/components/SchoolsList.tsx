import { useQuery } from "@tanstack/react-query";
import type {
  ColumnDef,
  PaginationState,
  OnChangeFn,
} from "@tanstack/react-table";
import { UploadSimpleIcon } from "@phosphor-icons/react";
import type { School } from "@/api/generated/types.gen";
import { listSchoolsOptions } from "@/features/schools/api/schools";
import { DataTable } from "@/components/DataTable";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useFormDialog } from "@/hooks/useFormDialog";
import { SchoolImportDialog } from "./SchoolImportDialog";

const columns: ColumnDef<School>[] = [
  {
    accessorKey: "code",
    header: "Code",
    cell: ({ getValue }) => (
      <span className="font-mono text-xs">{getValue<string>()}</span>
    ),
  },
  {
    accessorKey: "name",
    header: "Name",
  },
  {
    accessorKey: "city",
    header: "Borough",
  },
  {
    accessorKey: "address",
    header: "Address",
  },
];

interface Props {
  search: string;
  onSearchChange: (value: string) => void;
  pagination: PaginationState;
  onPaginationChange: OnChangeFn<PaginationState>;
  onRowClick: (school: School) => void;
}

export function SchoolsList({
  search,
  onSearchChange,
  pagination,
  onPaginationChange,
  onRowClick,
}: Props) {
  const importDialog = useFormDialog();

  const { data, isLoading, error } = useQuery(
    listSchoolsOptions({
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
        <h1 className="text-2xl font-semibold">Schools</h1>
        <div className="flex items-center gap-2">
          <Input
            placeholder="Search schools…"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-56"
          />
          <Button size="sm" onClick={() => importDialog.setOpen(true)}>
            <UploadSimpleIcon size={15} />
            Import CSV
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
            emptyMessage="No schools found."
            onRowClick={onRowClick}
          />
        </CardContent>
      </Card>

      <SchoolImportDialog
        open={importDialog.open}
        onOpenChange={importDialog.onOpenChange}
      />
    </div>
  );
}
