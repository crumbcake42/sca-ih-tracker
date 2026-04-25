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
import type { Contractor } from "@/api/generated/types.gen";
import {
  getContractorOptions,
  listContractorsQueryKey,
  getContractorQueryKey,
  deleteContractorMutation,
} from "@/features/contractors/api/contractors";
import { ContractorFormDialog } from "./ContractorFormDialog";

interface Props {
  contractorId: number;
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
  contractor: Contractor;
  onDeleted: () => void;
}

function DeleteConfirmDialog({
  open,
  onOpenChange,
  contractor,
  onDeleted,
}: DeleteDialogProps) {
  const queryClient = useQueryClient();
  const [inlineError, setInlineError] = useState<string | null>(null);

  const { mutate, isPending } = useMutation({
    ...deleteContractorMutation(),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: listContractorsQueryKey(),
      });
      void queryClient.removeQueries({
        queryKey: getContractorQueryKey({
          path: { contractor_id: contractor.id },
        }),
      });
      toast.success("Contractor deleted.");
      onDeleted();
    },
    onError: (err) => {
      const detail = is409DetailString(err);
      if (detail) {
        setInlineError(detail);
      } else {
        toast.error("Could not delete Contractor.");
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
          <DialogTitle>Delete Contractor</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Are you sure you want to delete{" "}
          <span className="font-medium text-foreground">{contractor.name}</span>
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
            onClick={() => mutate({ path: { contractor_id: contractor.id } })}
          >
            {isPending ? "Deleting…" : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ContractorDetail({ contractorId }: Props) {
  const navigate = useNavigate();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const {
    data: contractor,
    isLoading,
    error,
  } = useQuery(getContractorOptions({ path: { contractor_id: contractorId } }));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/admin/contractors">
            <ArrowLeftIcon size={15} />
            Contractors
          </Link>
        </Button>
        {contractor && (
          <h1 className="text-2xl font-semibold">{contractor.name}</h1>
        )}
      </div>

      <Card className="max-w-lg">
        <CardContent className="pt-4">
          {isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-6 w-full" />
              ))}
            </div>
          )}
          {error && (
            <p className="text-sm text-destructive">
              Could not load contractor details.
            </p>
          )}
          {contractor && (
            <>
              <dl>
                <DetailRow label="Name" value={contractor.name} />
                <DetailRow label="Address" value={contractor.address} />
                <DetailRow label="City" value={contractor.city} />
                <DetailRow label="State" value={contractor.state} />
                <DetailRow label="Zip code" value={contractor.zip_code} />
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

      {contractor && (
        <>
          <ContractorFormDialog
            open={editOpen}
            onOpenChange={setEditOpen}
            contractor={contractor}
          />
          <DeleteConfirmDialog
            open={deleteOpen}
            onOpenChange={setDeleteOpen}
            contractor={contractor}
            onDeleted={() => void navigate({ to: "/admin/contractors" })}
          />
        </>
      )}
    </div>
  );
}
