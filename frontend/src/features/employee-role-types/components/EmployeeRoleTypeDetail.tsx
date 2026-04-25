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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import type { EmployeeRoleTypeRead } from "@/api/generated/types.gen";
import {
  getEmployeeRoleTypeOptions,
  listEmployeeRoleTypesQueryKey,
  getEmployeeRoleTypeQueryKey,
  deleteEmployeeRoleTypeMutation,
} from "@/features/employee-role-types/api/employeeRoleTypes";
import { EmployeeRoleTypeFormDialog } from "./EmployeeRoleTypeFormDialog";

interface Props {
  roleTypeId: number;
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

interface DeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  roleType: EmployeeRoleTypeRead;
  onDeleted: () => void;
}

function DeleteConfirmDialog({
  open,
  onOpenChange,
  roleType,
  onDeleted,
}: DeleteDialogProps) {
  const queryClient = useQueryClient();
  const [inlineError, setInlineError] = useState<string | null>(null);

  const { mutate, isPending } = useMutation({
    ...deleteEmployeeRoleTypeMutation(),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: listEmployeeRoleTypesQueryKey(),
      });
      void queryClient.removeQueries({
        queryKey: getEmployeeRoleTypeQueryKey({
          path: { role_type_id: roleType.id },
        }),
      });
      toast.success("Employee role type deleted.");
      onDeleted();
    },
    onError: (err) => {
      const detail = is409DetailString(err);
      if (detail) {
        setInlineError(detail);
      } else {
        toast.error("Could not delete Employee Role Type.");
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
          <DialogTitle>Delete Employee Role Type</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Are you sure you want to delete{" "}
          <span className="font-medium text-foreground">{roleType.name}</span>?
          This cannot be undone.
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
            onClick={() => mutate({ path: { role_type_id: roleType.id } })}
          >
            {isPending ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function EmployeeRoleTypeDetail({ roleTypeId }: Props) {
  const navigate = useNavigate();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const {
    data: roleType,
    isLoading,
    error,
  } = useQuery(
    getEmployeeRoleTypeOptions({ path: { role_type_id: roleTypeId } }),
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/admin/employee-role-types">
            <ArrowLeftIcon size={15} />
            Employee Role Types
          </Link>
        </Button>
        {roleType && (
          <h1 className="text-2xl font-semibold">{roleType.name}</h1>
        )}
      </div>

      <Card className="max-w-lg">
        <CardContent className="pt-4">
          {isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 2 }).map((_, i) => (
                <Skeleton key={i} className="h-6 w-full" />
              ))}
            </div>
          )}
          {error && (
            <p className="text-sm text-destructive">
              Could not load employee role type details.
            </p>
          )}
          {roleType && (
            <>
              <dl>
                <DetailRow label="Name" value={roleType.name} />
                <DetailRow label="Description" value={roleType.description} />
              </dl>
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

      {roleType && (
        <>
          <EmployeeRoleTypeFormDialog
            open={editOpen}
            onOpenChange={setEditOpen}
            roleType={roleType}
          />
          <DeleteConfirmDialog
            open={deleteOpen}
            onOpenChange={setDeleteOpen}
            roleType={roleType}
            onDeleted={() =>
              void navigate({ to: "/admin/employee-role-types" })
            }
          />
        </>
      )}
    </div>
  );
}
