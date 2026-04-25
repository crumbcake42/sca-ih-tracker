import { useNavigate } from "@tanstack/react-router";
import { PlusIcon } from "@phosphor-icons/react";
import type { ColumnDef } from "@tanstack/react-table";
import type { Hygienist } from "@/api/generated/types.gen";
import { listHygienistsOptions } from "@/features/hygienists/api/hygienists";
import { HygienistFormDialog } from "@/features/hygienists/components/HygienistFormDialog";
import { EntityListPage } from "@/components/EntityListPage";
import { Button } from "@/components/ui/button";
import { useFormDialog } from "@/hooks/useFormDialog";

const columns: ColumnDef<Hygienist>[] = [
  {
    id: "name",
    header: "Name",
    accessorFn: (h) => `${h.first_name} ${h.last_name}`,
  },
  {
    accessorKey: "email",
    header: "Email",
  },
  {
    accessorKey: "phone",
    header: "Phone",
  },
];

export function HygienistListPage() {
  const navigate = useNavigate();
  const addDialog = useFormDialog();

  return (
    <>
      <EntityListPage<Hygienist>
        title="Hygienists"
        columns={columns}
        queryOptions={listHygienistsOptions}
        searchPlaceholder="Search hygienists…"
        emptyMessage="No hygienists found."
        actions={
          <Button size="sm" onClick={() => addDialog.setOpen(true)}>
            <PlusIcon size={15} />
            Add hygienist
          </Button>
        }
        onRowClick={(hygienist) =>
          void navigate({
            to: "/admin/hygienists/$hygienistId",
            params: { hygienistId: String(hygienist.id) },
          })
        }
      />
      <HygienistFormDialog
        open={addDialog.open}
        onOpenChange={addDialog.onOpenChange}
      />
    </>
  );
}
