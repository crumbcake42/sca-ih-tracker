import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import type { ColumnDef } from "@tanstack/react-table";
import { UploadSimpleIcon } from "@phosphor-icons/react";
import { listEntriesSchoolsGetOptions } from "@/api/generated/@tanstack/react-query.gen";
import type { School } from "@/api/generated/types.gen";
import { DataTable } from "@/components/DataTable";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useUrlSearch } from "@/hooks/useUrlSearch";
import { useUrlPagination } from "@/hooks/useUrlPagination";
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

export function SchoolsListPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useUrlSearch("search");
  const { pagination, onPaginationChange } = useUrlPagination();
  const importDialog = useFormDialog();

  const { data, isLoading, error } = useQuery(
    listEntriesSchoolsGetOptions({
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
            onChange={(e) => setSearch(e.target.value)}
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
            onRowClick={(row) =>
              void navigate({
                to: "/admin/schools/$schoolId",
                params: { schoolId: String(row.id) },
              })
            }
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
