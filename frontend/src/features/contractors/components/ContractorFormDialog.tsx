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
import type { Contractor } from "@/api/generated/types.gen";
import { useEntityForm } from "@/hooks/useEntityForm";
import {
  createContractorMutation,
  updateContractorMutation,
  listContractorsQueryKey,
  getContractorQueryKey,
} from "@/features/contractors/api/contractors";

const schema = z.object({
  name: z.string().min(1, "Name is required."),
  address: z.string().min(1, "Address is required."),
  city: z.string().min(1, "City is required."),
  state: z.string().min(1, "State is required."),
  zip_code: z.string().min(1, "Zip code is required."),
});

type FormValues = z.infer<typeof schema>;

const DEFAULT_VALUES: FormValues = {
  name: "",
  address: "",
  city: "",
  state: "",
  zip_code: "",
};

function toFormValues(c: Contractor): FormValues {
  return {
    name: c.name,
    address: c.address,
    city: c.city,
    state: c.state,
    zip_code: c.zip_code,
  };
}

function toBody(values: FormValues) {
  return {
    name: values.name,
    address: values.address,
    city: values.city,
    state: values.state,
    zip_code: values.zip_code,
  };
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  contractor?: Contractor;
}

export function ContractorFormDialog({
  open,
  onOpenChange,
  contractor,
}: Props) {
  const isEdit = !!contractor;

  const { form, onSubmit, isPending } = useEntityForm({
    entity: contractor,
    open,
    schema,
    defaultValues: DEFAULT_VALUES,
    toFormValues,
    createMutationOptions: createContractorMutation(),
    updateMutationOptions: updateContractorMutation(),
    buildCreateVars: (values) => ({ body: toBody(values) }),
    buildUpdateVars: (values, c) => ({
      path: { contractor_id: c.id },
      body: toBody(values),
    }),
    invalidateKeys: (c) =>
      c
        ? [
            listContractorsQueryKey(),
            getContractorQueryKey({ path: { contractor_id: c.id } }),
          ]
        : [listContractorsQueryKey()],
    entityLabel: "Contractor",
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
            {isEdit ? "Edit Contractor" : "Add Contractor"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Field data-invalid={!!errors.name}>
            <FieldLabel htmlFor="con-name">Name</FieldLabel>
            <Input
              id="con-name"
              aria-invalid={!!errors.name}
              {...register("name")}
            />
            <FieldError errors={[errors.name]} />
          </Field>

          <Field data-invalid={!!errors.address}>
            <FieldLabel htmlFor="con-address">Address</FieldLabel>
            <Input
              id="con-address"
              aria-invalid={!!errors.address}
              {...register("address")}
            />
            <FieldError errors={[errors.address]} />
          </Field>

          <Field data-invalid={!!errors.city}>
            <FieldLabel htmlFor="con-city">City</FieldLabel>
            <Input
              id="con-city"
              aria-invalid={!!errors.city}
              {...register("city")}
            />
            <FieldError errors={[errors.city]} />
          </Field>

          <Field data-invalid={!!errors.state}>
            <FieldLabel htmlFor="con-state">State</FieldLabel>
            <Input
              id="con-state"
              aria-invalid={!!errors.state}
              {...register("state")}
            />
            <FieldError errors={[errors.state]} />
          </Field>

          <Field data-invalid={!!errors.zip_code}>
            <FieldLabel htmlFor="con-zip">Zip code</FieldLabel>
            <Input
              id="con-zip"
              aria-invalid={!!errors.zip_code}
              {...register("zip_code")}
            />
            <FieldError errors={[errors.zip_code]} />
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
