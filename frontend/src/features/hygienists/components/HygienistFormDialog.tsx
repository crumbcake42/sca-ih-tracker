import { z } from "zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Field, FieldLabel, FieldError } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { Hygienist } from "@/api/generated/types.gen";
import { useEntityForm } from "@/hooks/useEntityForm";
import {
  createHygienistMutation,
  updateHygienistMutation,
  listHygienistsQueryKey,
  getHygienistQueryKey,
} from "@/features/hygienists/api/hygienists";

const schema = z.object({
  first_name: z.string().min(1, "First name is required."),
  last_name: z.string().min(1, "Last name is required."),
  email: z.string().email("Invalid email.").or(z.literal("")).optional(),
  phone: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const DEFAULT_VALUES: FormValues = {
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
};

function toFormValues(h: Hygienist): FormValues {
  return {
    first_name: h.first_name,
    last_name: h.last_name,
    email: h.email ?? "",
    phone: h.phone ?? "",
  };
}

function toBody(values: FormValues) {
  return {
    first_name: values.first_name,
    last_name: values.last_name,
    email: values.email || null,
    phone: values.phone || null,
  };
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  hygienist?: Hygienist;
}

export function HygienistFormDialog({ open, onOpenChange, hygienist }: Props) {
  const isEdit = !!hygienist;

  const { form, onSubmit, isPending } = useEntityForm({
    entity: hygienist,
    open,
    schema,
    defaultValues: DEFAULT_VALUES,
    toFormValues,
    createMutationOptions: createHygienistMutation(),
    updateMutationOptions: updateHygienistMutation(),
    buildCreateVars: (values) => ({ body: toBody(values) }),
    buildUpdateVars: (values, h) => ({
      path: { hygienist_id: h.id },
      body: toBody(values),
    }),
    invalidateKeys: (h) =>
      h
        ? [
            listHygienistsQueryKey(),
            getHygienistQueryKey({ path: { hygienist_id: h.id } }),
          ]
        : [listHygienistsQueryKey()],
    entityLabel: "Hygienist",
    onSuccess: () => onOpenChange(false),
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = form;

  const handleOpenChange = (next: boolean) => {
    if (!next) form.reset();
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Edit Hygienist" : "Add Hygienist"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Field data-invalid={!!errors.first_name}>
            <FieldLabel htmlFor="hyg-first-name">First name</FieldLabel>
            <Input
              id="hyg-first-name"
              aria-invalid={!!errors.first_name}
              {...register("first_name")}
            />
            <FieldError errors={[errors.first_name]} />
          </Field>

          <Field data-invalid={!!errors.last_name}>
            <FieldLabel htmlFor="hyg-last-name">Last name</FieldLabel>
            <Input
              id="hyg-last-name"
              aria-invalid={!!errors.last_name}
              {...register("last_name")}
            />
            <FieldError errors={[errors.last_name]} />
          </Field>

          <Field data-invalid={!!errors.email}>
            <FieldLabel htmlFor="hyg-email">Email</FieldLabel>
            <Input
              id="hyg-email"
              type="email"
              aria-invalid={!!errors.email}
              {...register("email")}
            />
            <FieldError errors={[errors.email]} />
          </Field>

          <Field data-invalid={!!errors.phone}>
            <FieldLabel htmlFor="hyg-phone">Phone</FieldLabel>
            <Input
              id="hyg-phone"
              aria-invalid={!!errors.phone}
              {...register("phone")}
            />
            <FieldError errors={[errors.phone]} />
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
              {isPending ? "Saving…" : isEdit ? "Save changes" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
