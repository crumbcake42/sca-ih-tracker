import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import type { Employee } from "@/api/generated/types.gen";
import { EmployeesList } from "@/features/employees/components/EmployeesList";
import { EmployeeFormDialog } from "@/features/employees/components/EmployeeFormDialog";
import { useUrlSearch } from "@/hooks/useUrlSearch";
import { useUrlPagination } from "@/hooks/useUrlPagination";

export function EmployeesListPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useUrlSearch("search");
  const { pagination, onPaginationChange } = useUrlPagination();
  const [addOpen, setAddOpen] = useState(false);

  function handleRowClick(employee: Employee) {
    void navigate({
      to: "/admin/employees/$employeeId",
      params: { employeeId: String(employee.id) },
    });
  }

  return (
    <>
      <EmployeesList
        search={search}
        onSearchChange={setSearch}
        pagination={pagination}
        onPaginationChange={onPaginationChange}
        onRowClick={handleRowClick}
        onAddClick={() => setAddOpen(true)}
      />
      <EmployeeFormDialog open={addOpen} onOpenChange={setAddOpen} />
    </>
  );
}
