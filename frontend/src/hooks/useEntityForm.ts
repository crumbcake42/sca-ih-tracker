import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type {
  UseFormReturn,
  FieldValues,
  DefaultValues,
} from "react-hook-form";
import type { QueryKey, MutationFunction } from "@tanstack/react-query";
import type { ZodType } from "zod";
import { applyServerErrors } from "@/lib/form-errors";

export interface UseEntityFormArgs<
  TEntity,
  TFormValues extends FieldValues,
  TCreateVars,
  TUpdateVars,
> {
  entity?: TEntity;
  /** Controls the reset effect — pass the dialog's open state. */
  open: boolean;
  schema: ZodType<TFormValues>;
  defaultValues: TFormValues;
  toFormValues: (entity: TEntity) => TFormValues;
  createMutationOptions: {
    mutationFn?: MutationFunction<unknown, TCreateVars>;
  };
  updateMutationOptions: {
    mutationFn?: MutationFunction<unknown, TUpdateVars>;
  };
  buildCreateVars: (values: TFormValues) => TCreateVars;
  buildUpdateVars: (values: TFormValues, entity: TEntity) => TUpdateVars;
  /**
   * Returns query keys to invalidate on success.
   * Called with `undefined` on create (entity doesn't exist yet)
   * and with the existing entity on update.
   */
  invalidateKeys: (entity?: TEntity) => readonly QueryKey[];
  /** Used in toast copy: "Employee created." / "Could not create employee." */
  entityLabel: string;
  /** Called after a successful mutation (e.g. close dialog). */
  onSuccess?: () => void;
}

/** Returned form handle plus submission utilities. */
interface UseEntityFormReturn<TFormValues extends FieldValues> {
  form: UseFormReturn<TFormValues>;
  /** Pass to `form.handleSubmit(onSubmit)` in the dialog's `<form>`. */
  onSubmit: (values: TFormValues) => void;
  isPending: boolean;
  isEdit: boolean;
}

/**
 * Encapsulates the create/edit form lifecycle for a single admin entity:
 * RHF setup, reset-on-open, dual mutations, invalidation, and error handling.
 * Entity-specific dialogs provide the fields JSX and Dialog shell.
 */
export function useEntityForm<
  TEntity,
  TFormValues extends FieldValues,
  TCreateVars,
  TUpdateVars,
>(
  args: UseEntityFormArgs<TEntity, TFormValues, TCreateVars, TUpdateVars>,
): UseEntityFormReturn<TFormValues> {
  const {
    entity,
    open,
    schema,
    defaultValues,
    toFormValues,
    createMutationOptions,
    updateMutationOptions,
    buildCreateVars,
    buildUpdateVars,
    invalidateKeys,
    entityLabel,
    onSuccess,
  } = args;

  const queryClient = useQueryClient();
  const isEdit = !!entity;

  const form = useForm<TFormValues>({
    resolver: standardSchemaResolver(schema as any),
    defaultValues: (entity
      ? toFormValues(entity)
      : defaultValues) as DefaultValues<TFormValues>,
  }) as UseFormReturn<TFormValues>;

  useEffect(() => {
    if (open) {
      form.reset(entity ? toFormValues(entity) : defaultValues);
    }
    // Intentionally omit reset and toFormValues from deps — they are stable
    // references and including them causes spurious resets when parent rerenders.
  }, [open, entity]);

  const { mutate: create, isPending: isCreating } = useMutation<
    unknown,
    unknown,
    TCreateVars
  >({
    ...createMutationOptions,
    onSuccess() {
      for (const key of invalidateKeys(undefined)) {
        void queryClient.invalidateQueries({ queryKey: key });
      }
      toast.success(`${entityLabel} created.`);
      onSuccess?.();
    },
    onError(err) {
      if (!applyServerErrors(err, form.setError)) {
        toast.error(`Could not create ${entityLabel.toLowerCase()}.`);
      }
    },
  });

  const { mutate: update, isPending: isUpdating } = useMutation<
    unknown,
    unknown,
    TUpdateVars
  >({
    ...updateMutationOptions,
    onSuccess() {
      for (const key of invalidateKeys(entity)) {
        void queryClient.invalidateQueries({ queryKey: key });
      }
      toast.success(`${entityLabel} updated.`);
      onSuccess?.();
    },
    onError(err) {
      if (!applyServerErrors(err, form.setError)) {
        toast.error(`Could not update ${entityLabel.toLowerCase()}.`);
      }
    },
  });

  const onSubmit = (values: TFormValues) => {
    if (isEdit && entity) {
      update(buildUpdateVars(values, entity));
    } else {
      create(buildCreateVars(values));
    }
  };

  return { form, onSubmit, isPending: isCreating || isUpdating, isEdit };
}
