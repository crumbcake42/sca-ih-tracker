import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeftIcon,
  PencilSimpleIcon,
  TrashIcon,
} from "@phosphor-icons/react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import type { Employee } from "@/api/generated/types.gen";
import {
  getEmployeeOptions,
  listEmployeesQueryKey,
  getEmployeeQueryKey,
  deleteEmployeeMutation,
} from "@/features/employees/api/employees";
import { EmployeeFormDialog } from "./EmployeeFormDialog";
import { EmployeeRolesTab } from "./EmployeeRolesTab";

interface Props {
  employeeId: number;
}

function DetailRow({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  return (
    <div className="flex items-baseline gap-4 py-2 border-b last:border-0">
      <dt className="w-32 shrink-0 text-sm text-muted-foreground">{label}</dt>
      <dd className="text-sm">{value ?? "—"}</dd>
    </div>
  );
}

function is409DetailString(err: unknown): string | null {
  if (
    typeof err === "object" &&
    err !== null &&
    "detail" in err &&
    typeof (err as { detail: unknown }).detail === "string"
  ) {
    return (err as { detail: string }).detail;
  }
  return null;
}

function DetailsTab({ employee }: { employee: Employee }) {
  return (
    <dl>
      <DetailRow label="First name" value={employee.first_name} />
      <DetailRow label="Last name" value={employee.last_name} />
      <DetailRow label="Display name" value={employee.display_name} />
      <DetailRow label="Title" value={employee.title} />
      <DetailRow label="Email" value={employee.email} />
      <DetailRow label="Phone" value={employee.phone} />
      <DetailRow label="ADP ID" value={employee.adp_id} />
    </dl>
  );
}

interface DeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  employee: Employee;
  onDeleted: () => void;
}

function DeleteConfirmDialog({
  open,
  onOpenChange,
  employee,
  onDeleted,
}: DeleteDialogProps) {
  const queryClient = useQueryClient();
  const [inlineError, setInlineError] = useState<string | null>(null);

  const { mutate, isPending } = useMutation({
    ...deleteEmployeeMutation(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: listEmployeesQueryKey() });
      void queryClient.removeQueries({
        queryKey: getEmployeeQueryKey({ path: { employee_id: employee.id } }),
      });
      toast.success("Employee deleted.");
      onDeleted();
    },
    onError: (err) => {
      const detail = is409DetailString(err);
      if (detail) {
        setInlineError(detail);
      } else {
        toast.error("Could not delete employee.");
        onOpenChange(false);
      }
    },
  });

  const handleOpenChange = (next: boolean) => {
    if (!next) setInlineError(null);
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Employee</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Are you sure you want to delete{" "}
          <span className="font-medium text-foreground">
            {employee.display_name ??
              `${employee.first_name} ${employee.last_name}`}
          </span>
          ? This cannot be undone.
        </p>
        {inlineError && (
          <p className="rounded-none border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {inlineError}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={isPending}
            onClick={() => mutate({ path: { employee_id: employee.id } })}
          >
            {isPending ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function EmployeeDetail({ employeeId }: Props) {
  const navigate = useNavigate();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const {
    data: employee,
    isLoading,
    error,
  } = useQuery(getEmployeeOptions({ path: { employee_id: employeeId } }));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/admin/employees">
            <ArrowLeftIcon size={15} />
            Employees
          </Link>
        </Button>
        {employee && (
          <h1 className="text-2xl font-semibold">
            {employee.display_name ??
              `${employee.first_name} ${employee.last_name}`}
          </h1>
        )}
      </div>

      <Tabs defaultValue="details">
        <TabsList>
          <TabsTrigger value="details">Details</TabsTrigger>
          <TabsTrigger value="roles">Roles</TabsTrigger>
        </TabsList>

        <TabsContent value="details">
          <Card className="max-w-lg">
            <CardContent className="pt-4">
              {isLoading && (
                <div className="space-y-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <Skeleton key={i} className="h-6 w-full" />
                  ))}
                </div>
              )}
              {error && (
                <p className="text-sm text-destructive">
                  Could not load employee details.
                </p>
              )}
              {employee && (
                <>
                  <DetailsTab employee={employee} />
                  <div className="mt-4 flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setEditOpen(true)}
                    >
                      <PencilSimpleIcon size={14} />
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => setDeleteOpen(true)}
                    >
                      <TrashIcon size={14} />
                      Delete
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="roles">
          <EmployeeRolesTab employeeId={employeeId} />
        </TabsContent>
      </Tabs>

      {employee && (
        <>
          <EmployeeFormDialog
            open={editOpen}
            onOpenChange={setEditOpen}
            employee={employee}
          />
          <DeleteConfirmDialog
            open={deleteOpen}
            onOpenChange={setDeleteOpen}
            employee={employee}
            onDeleted={() => void navigate({ to: "/admin/employees" })}
          />
        </>
      )}
    </div>
  );
}
