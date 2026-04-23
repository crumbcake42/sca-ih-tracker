import { useForm, Controller } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Field, FieldLabel, FieldError } from "@/components/ui/field";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { applyServerErrors } from "@/lib/form-errors";
import type { NoteEntityType } from "@/api/generated/types.gen";
import {
  createNoteMutation,
  listNotesQueryKey,
} from "@/features/notes/api/notes";

const schema = z.object({
  body: z.string().min(1, "Note body is required."),
  is_blocking: z.boolean().default(false),
});

type FormValues = z.infer<typeof schema>;

interface Props {
  entityType: NoteEntityType;
  entityId: number;
}

/** Inline form for creating a new top-level note on an entity. */
export function NoteComposer({ entityType, entityId }: Props) {
  const queryClient = useQueryClient();
  const {
    register,
    control,
    handleSubmit,
    setError,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: standardSchemaResolver(schema),
    defaultValues: { body: "", is_blocking: false },
  });

  const { mutate, isPending } = useMutation({
    ...createNoteMutation(),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: listNotesQueryKey({
          path: { entity_type: entityType, entity_id: entityId },
        }),
      });
      toast.success("Note added.");
      reset();
    },
    onError: (err) => {
      if (!applyServerErrors(err, setError)) {
        toast.error("Could not add note.");
      }
    },
  });

  const onSubmit = (values: FormValues) => {
    mutate({
      path: { entity_type: entityType, entity_id: entityId },
      body: { body: values.body, is_blocking: values.is_blocking },
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
      <Field data-invalid={!!errors.body}>
        <FieldLabel htmlFor="note-body">Add a note</FieldLabel>
        <Textarea
          id="note-body"
          placeholder="Write a note…"
          aria-invalid={!!errors.body}
          {...register("body")}
        />
        <FieldError errors={[errors.body]} />
      </Field>
      <div className="flex items-center justify-between gap-4">
        <Field orientation="horizontal" className="w-auto gap-2">
          <Controller
            control={control}
            name="is_blocking"
            render={({ field }) => (
              <Checkbox
                id="note-blocking"
                checked={field.value}
                onCheckedChange={field.onChange}
              />
            )}
          />
          <FieldLabel htmlFor="note-blocking" className="text-xs font-normal">
            Mark as blocking
          </FieldLabel>
        </Field>
        <Button type="submit" size="sm" disabled={isPending}>
          {isPending ? "Adding…" : "Add note"}
        </Button>
      </div>
    </form>
  );
}
