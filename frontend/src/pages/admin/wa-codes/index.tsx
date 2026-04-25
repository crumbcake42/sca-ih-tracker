import { useNavigate } from "@tanstack/react-router";
import { PlusIcon } from "@phosphor-icons/react";
import type { ColumnDef } from "@tanstack/react-table";
import type { WaCode } from "@/api/generated/types.gen";
import { listWaCodesOptions } from "@/features/wa-codes/api/wa-codes";
import { WaCodeFormDialog } from "@/features/wa-codes/components/WaCodeFormDialog";
import { EntityListPage } from "@/components/EntityListPage";
import { Button } from "@/components/ui/button";
import { useFormDialog } from "@/hooks/useFormDialog";

const columns: ColumnDef<WaCode>[] = [
  {
    accessorKey: "code",
    header: "Code",
    cell: ({ getValue }) => (
      <span className="font-mono text-sm">{getValue<string>()}</span>
    ),
  },
  {
    accessorKey: "description",
    header: "Description",
  },
  {
    accessorKey: "level",
    header: "Level",
    cell: ({ getValue }) => {
      const v = getValue<string>();
      return v.charAt(0).toUpperCase() + v.slice(1);
    },
  },
  {
    accessorKey: "default_fee",
    header: "Default fee",
    cell: ({ getValue }) => {
      const v = getValue<string | null>();
      return v != null ? `$${v}` : "—";
    },
  },
];

export function WaCodeListPage() {
  const navigate = useNavigate();
  const addDialog = useFormDialog();

  return (
    <>
      <EntityListPage<WaCode>
        title="WA Codes"
        columns={columns}
        queryOptions={listWaCodesOptions}
        searchPlaceholder="Search WA codes…"
        emptyMessage="No WA codes found."
        actions={
          <Button size="sm" onClick={() => addDialog.setOpen(true)}>
            <PlusIcon size={15} />
            Add WA code
          </Button>
        }
        onRowClick={(waCode) =>
          void navigate({
            to: "/admin/wa-codes/$waCodeId",
            params: { waCodeId: String(waCode.id) },
          })
        }
      />
      <WaCodeFormDialog
        open={addDialog.open}
        onOpenChange={addDialog.onOpenChange}
      />
    </>
  );
}
