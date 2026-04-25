import { useNavigate } from "@tanstack/react-router";
import { UploadSimpleIcon } from "@phosphor-icons/react";
import type { ColumnDef } from "@tanstack/react-table";
import type { School } from "@/api/generated/types.gen";
import { listSchoolsOptions } from "@/features/schools/api/schools";
import { SchoolImportDialog } from "@/features/schools/components/SchoolImportDialog";
import { EntityListPage } from "@/components/EntityListPage";
import { Button } from "@/components/ui/button";
import { useFormDialog } from "@/hooks/useFormDialog";

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
  const importDialog = useFormDialog();

  return (
    <>
      <EntityListPage<School>
        title="Schools"
        columns={columns}
        queryOptions={listSchoolsOptions}
        searchPlaceholder="Search schools…"
        emptyMessage="No schools found."
        actions={
          <Button size="sm" onClick={() => importDialog.setOpen(true)}>
            <UploadSimpleIcon size={15} />
            Import CSV
          </Button>
        }
        onRowClick={(school) =>
          void navigate({
            to: "/admin/schools/$schoolId",
            params: { schoolId: String(school.id) },
          })
        }
      />
      <SchoolImportDialog
        open={importDialog.open}
        onOpenChange={importDialog.onOpenChange}
      />
    </>
  );
}
