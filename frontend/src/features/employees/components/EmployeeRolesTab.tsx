import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PlusIcon, PencilSimpleIcon, TrashIcon } from "@phosphor-icons/react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { EmployeeRole } from "@/api/generated/types.gen";
import {
  listEmployeeRolesOptions,
  listEmployeeRolesQueryKey,
  deleteEmployeeRoleMutation,
} from "@/features/employees/api/employees";
import { EmployeeRoleFormDialog } from "./EmployeeRoleFormDialog";

interface Props {
  employeeId: number;
}

interface DeleteDialogProps {
  role: EmployeeRole | null;
  onClose: () => void;
  employeeId: number;
}

function DeleteRoleDialog({ role, onClose, employeeId }: DeleteDialogProps) {
  const queryClient = useQueryClient();

  const { mutate, isPending } = useMutation({
    ...deleteEmployeeRoleMutation(),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: listEmployeeRolesQueryKey({
          path: { employee_id: employeeId },
        }),
      });
      toast.success("Role deleted.");
      onClose();
    },
    onError: () => {
      toast.error("Could not delete role.");
      onClose();
    },
  });

  return (
    <Dialog open={!!role} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Role</DialogTitle>
        </DialogHeader>
        {role && (
          <p className="text-sm text-muted-foreground">
            Delete{" "}
            <span className="font-medium text-foreground">
              {role.role_type}
            </span>{" "}
            starting {role.start_date}? This cannot be undone.
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={isPending || !role}
            onClick={() => role && mutate({ path: { role_id: role.id } })}
          >
            {isPending ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Roles tab content for the employee detail page. Lists all roles with add/edit/delete actions. */
export function EmployeeRolesTab({ employeeId }: Props) {
  const [addOpen, setAddOpen] = useState(false);
  const [editRole, setEditRole] = useState<EmployeeRole | null>(null);
  const [deleteRole, setDeleteRole] = useState<EmployeeRole | null>(null);

  const {
    data: roles,
    isLoading,
    error,
  } = useQuery(listEmployeeRolesOptions({ path: { employee_id: employeeId } }));

  return (
    <div className="max-w-3xl space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium">Roles</h2>
        <Button size="sm" onClick={() => setAddOpen(true)}>
          <PlusIcon size={15} />
          Add role
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading && (
            <div className="space-y-2 p-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-6 w-full" />
              ))}
            </div>
          )}
          {error && (
            <p className="p-4 text-sm text-destructive">
              Could not load roles.
            </p>
          )}
          {roles && roles.length === 0 && (
            <p className="p-4 text-sm text-muted-foreground">No roles yet.</p>
          )}
          {roles && roles.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Role type</TableHead>
                  <TableHead>Start date</TableHead>
                  <TableHead>End date</TableHead>
                  <TableHead>Hourly rate</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {roles.map((role) => (
                  <TableRow key={role.id}>
                    <TableCell>{role.role_type}</TableCell>
                    <TableCell>{role.start_date}</TableCell>
                    <TableCell>{role.end_date ?? "—"}</TableCell>
                    <TableCell>${role.hourly_rate}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setEditRole(role)}
                        >
                          <PencilSimpleIcon size={13} />
                          Edit
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-destructive hover:text-destructive"
                          onClick={() => setDeleteRole(role)}
                        >
                          <TrashIcon size={13} />
                          Delete
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <EmployeeRoleFormDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        employeeId={employeeId}
      />

      <EmployeeRoleFormDialog
        open={!!editRole}
        onOpenChange={(open) => !open && setEditRole(null)}
        employeeId={employeeId}
        role={editRole ?? undefined}
      />

      <DeleteRoleDialog
        role={deleteRole}
        onClose={() => setDeleteRole(null)}
        employeeId={employeeId}
      />
    </div>
  );
}
