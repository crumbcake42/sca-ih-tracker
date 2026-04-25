import { useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { PlusIcon } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { EmployeeRoleTypeRead } from "@/api/generated/types.gen";
import { listEmployeeRoleTypesOptions } from "@/features/employee-role-types/api/employeeRoleTypes";
import { EmployeeRoleTypeFormDialog } from "@/features/employee-role-types/components/EmployeeRoleTypeFormDialog";
import { useFormDialog } from "@/hooks/useFormDialog";

export function EmployeeRoleTypeListPage() {
  const navigate = useNavigate();
  const addDialog = useFormDialog();

  const { data, isLoading, error } = useQuery(listEmployeeRoleTypesOptions());
  const rows: EmployeeRoleTypeRead[] = data ?? [];

  return (
    <>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Employee Role Types</h1>
          <Button size="sm" onClick={() => addDialog.setOpen(true)}>
            <PlusIcon size={15} />
            Add role type
          </Button>
        </div>

        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Description</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {error ? (
                  <TableRow>
                    <TableCell
                      colSpan={2}
                      className="py-8 text-center text-destructive"
                    >
                      {error instanceof Error
                        ? error.message
                        : "An error occurred."}
                    </TableCell>
                  </TableRow>
                ) : isLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <TableRow key={i}>
                      <TableCell>
                        <Skeleton className="h-4 w-full" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-full" />
                      </TableCell>
                    </TableRow>
                  ))
                ) : rows.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={2}
                      className="py-8 text-center text-muted-foreground"
                    >
                      No employee role types found.
                    </TableCell>
                  </TableRow>
                ) : (
                  rows.map((row) => (
                    <TableRow
                      key={row.id}
                      className="cursor-pointer"
                      onClick={() =>
                        void navigate({
                          to: "/admin/employee-role-types/$roleTypeId",
                          params: { roleTypeId: String(row.id) },
                        })
                      }
                    >
                      <TableCell className="font-medium">{row.name}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {row.description ?? "—"}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      <EmployeeRoleTypeFormDialog
        open={addDialog.open}
        onOpenChange={addDialog.onOpenChange}
      />
    </>
  );
}
