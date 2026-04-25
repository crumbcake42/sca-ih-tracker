import { useNavigate } from "@tanstack/react-router";
import { PlusIcon } from "@phosphor-icons/react";
import type { ColumnDef } from "@tanstack/react-table";
import type { Contractor } from "@/api/generated/types.gen";
import { listContractorsOptions } from "@/features/contractors/api/contractors";
import { ContractorFormDialog } from "@/features/contractors/components/ContractorFormDialog";
import { EntityListPage } from "@/components/EntityListPage";
import { Button } from "@/components/ui/button";
import { useFormDialog } from "@/hooks/useFormDialog";

const columns: ColumnDef<Contractor>[] = [
  {
    accessorKey: "name",
    header: "Name",
  },
  {
    accessorKey: "city",
    header: "City",
  },
  {
    accessorKey: "state",
    header: "State",
  },
  {
    accessorKey: "zip_code",
    header: "Zip code",
  },
];

export function ContractorListPage() {
  const navigate = useNavigate();
  const addDialog = useFormDialog();

  return (
    <>
      <EntityListPage<Contractor>
        title="Contractors"
        columns={columns}
        queryOptions={listContractorsOptions}
        searchPlaceholder="Search contractors…"
        emptyMessage="No contractors found."
        actions={
          <Button size="sm" onClick={() => addDialog.setOpen(true)}>
            <PlusIcon size={15} />
            Add contractor
          </Button>
        }
        onRowClick={(contractor) =>
          void navigate({
            to: "/admin/contractors/$contractorId",
            params: { contractorId: String(contractor.id) },
          })
        }
      />
      <ContractorFormDialog
        open={addDialog.open}
        onOpenChange={addDialog.onOpenChange}
      />
    </>
  );
}
