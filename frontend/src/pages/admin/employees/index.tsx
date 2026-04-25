import { useNavigate } from "@tanstack/react-router";
import { PlusIcon } from "@phosphor-icons/react";
import type { ColumnDef } from "@tanstack/react-table";
import type { Employee } from "@/api/generated/types.gen";
import { listEmployeesOptions } from "@/features/employees/api/employees";
import { EmployeeFormDialog } from "@/features/employees/components/EmployeeFormDialog";
import { EntityListPage } from "@/components/EntityListPage";
import { Button } from "@/components/ui/button";
import { useFormDialog } from "@/hooks/useFormDialog";

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

export function EmployeesListPage() {
  const navigate = useNavigate();
  const addDialog = useFormDialog();

  return (
    <>
      <EntityListPage<Employee>
        title="Employees"
        columns={columns}
        queryOptions={listEmployeesOptions}
        searchPlaceholder="Search employees…"
        emptyMessage="No employees found."
        actions={
          <Button size="sm" onClick={() => addDialog.setOpen(true)}>
            <PlusIcon size={15} />
            Add employee
          </Button>
        }
        onRowClick={(employee) =>
          void navigate({
            to: "/admin/employees/$employeeId",
            params: { employeeId: String(employee.id) },
          })
        }
      />
      <EmployeeFormDialog
        open={addDialog.open}
        onOpenChange={addDialog.onOpenChange}
      />
    </>
  );
}
