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
import type { Hygienist } from "@/api/generated/types.gen";
import {
  getHygienistOptions,
  listHygienistsQueryKey,
  getHygienistQueryKey,
  deleteHygienistMutation,
} from "@/features/hygienists/api/hygienists";
import { HygienistFormDialog } from "./HygienistFormDialog";

interface Props {
  hygienistId: number;
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
  hygienist: Hygienist;
  onDeleted: () => void;
}

function DeleteConfirmDialog({
  open,
  onOpenChange,
  hygienist,
  onDeleted,
}: DeleteDialogProps) {
  const queryClient = useQueryClient();
  const [inlineError, setInlineError] = useState<string | null>(null);

  const { mutate, isPending } = useMutation({
    ...deleteHygienistMutation(),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: listHygienistsQueryKey(),
      });
      void queryClient.removeQueries({
        queryKey: getHygienistQueryKey({
          path: { hygienist_id: hygienist.id },
        }),
      });
      toast.success("Hygienist deleted.");
      onDeleted();
    },
    onError: (err) => {
      const detail = is409DetailString(err);
      if (detail) {
        setInlineError(detail);
      } else {
        toast.error("Could not delete Hygienist.");
        onOpenChange(false);
      }
    },
  });

  const handleOpenChange = (next: boolean) => {
    if (!next) setInlineError(null);
    onOpenChange(next);
  };

  const fullName = `${hygienist.first_name} ${hygienist.last_name}`;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Hygienist</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Are you sure you want to delete{" "}
          <span className="font-medium text-foreground">{fullName}</span>? This
          cannot be undone.
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
            onClick={() => mutate({ path: { hygienist_id: hygienist.id } })}
          >
            {isPending ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function HygienistDetail({ hygienistId }: Props) {
  const navigate = useNavigate();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const {
    data: hygienist,
    isLoading,
    error,
  } = useQuery(getHygienistOptions({ path: { hygienist_id: hygienistId } }));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/admin/hygienists">
            <ArrowLeftIcon size={15} />
            Hygienists
          </Link>
        </Button>
        {hygienist && (
          <h1 className="text-2xl font-semibold">
            {hygienist.first_name} {hygienist.last_name}
          </h1>
        )}
      </div>

      <Card className="max-w-lg">
        <CardContent className="pt-4">
          {isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-6 w-full" />
              ))}
            </div>
          )}
          {error && (
            <p className="text-sm text-destructive">
              Could not load hygienist details.
            </p>
          )}
          {hygienist && (
            <>
              <dl>
                <DetailRow label="First name" value={hygienist.first_name} />
                <DetailRow label="Last name" value={hygienist.last_name} />
                <DetailRow label="Email" value={hygienist.email} />
                <DetailRow label="Phone" value={hygienist.phone} />
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

      {hygienist && (
        <>
          <HygienistFormDialog
            open={editOpen}
            onOpenChange={setEditOpen}
            hygienist={hygienist}
          />
          <DeleteConfirmDialog
            open={deleteOpen}
            onOpenChange={setDeleteOpen}
            hygienist={hygienist}
            onDeleted={() => void navigate({ to: "/admin/hygienists" })}
          />
        </>
      )}
    </div>
  );
}
