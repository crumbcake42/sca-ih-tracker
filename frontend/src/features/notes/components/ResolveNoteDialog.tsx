import { useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Field, FieldLabel, FieldError } from "@/components/ui/field";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import type { NoteEntityType } from "@/api/generated/types.gen";
import {
  resolveNoteMutation,
  listNotesQueryKey,
} from "@/features/notes/api/notes";

const schema = z.object({
  resolution_note: z.string().min(1, "Resolution note is required."),
});

type FormValues = z.infer<typeof schema>;

interface Props {
  noteId: number;
  entityType: NoteEntityType;
  entityId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Dialog for resolving a note, requiring a mandatory resolution_note. */
export function ResolveNoteDialog({
  noteId,
  entityType,
  entityId,
  open,
  onOpenChange,
}: Props) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: standardSchemaResolver(schema),
    defaultValues: { resolution_note: "" },
  });

  const { mutate, isPending } = useMutation({
    ...resolveNoteMutation(),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: listNotesQueryKey({
          path: { entity_type: entityType, entity_id: entityId },
        }),
      });
      toast.success("Note resolved.");
      reset();
      onOpenChange(false);
    },
    onError: () => {
      toast.error("Could not resolve note.");
    },
  });

  const handleOpenChange = (next: boolean) => {
    if (!next) reset();
    onOpenChange(next);
  };

  const onSubmit = (values: FormValues) => {
    mutate({
      path: { note_id: noteId },
      body: { resolution_note: values.resolution_note },
    });
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Resolve Note</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Field data-invalid={!!errors.resolution_note}>
            <FieldLabel htmlFor="resolution-note">Resolution note</FieldLabel>
            <Textarea
              id="resolution-note"
              placeholder="Describe how this was resolved…"
              aria-invalid={!!errors.resolution_note}
              {...register("resolution_note")}
            />
            <FieldError errors={[errors.resolution_note]} />
          </Field>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Resolving…" : "Resolve"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
