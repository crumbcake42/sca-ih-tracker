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
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import type { EmployeeRoleTypeRead } from "@/api/generated/types.gen";
import { useEntityForm } from "@/hooks/useEntityForm";
import {
  createEmployeeRoleTypeMutation,
  updateEmployeeRoleTypeMutation,
  listEmployeeRoleTypesQueryKey,
  getEmployeeRoleTypeQueryKey,
} from "@/features/employee-role-types/api/employeeRoleTypes";

const schema = z.object({
  name: z.string().min(1, "Name is required."),
  description: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const DEFAULT_VALUES: FormValues = {
  name: "",
  description: "",
};

function toFormValues(r: EmployeeRoleTypeRead): FormValues {
  return {
    name: r.name,
    description: r.description ?? "",
  };
}

function toBody(values: FormValues) {
  return {
    name: values.name,
    description: values.description || null,
  };
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  roleType?: EmployeeRoleTypeRead;
}

export function EmployeeRoleTypeFormDialog({
  open,
  onOpenChange,
  roleType,
}: Props) {
  const isEdit = !!roleType;

  const { form, onSubmit, isPending } = useEntityForm({
    entity: roleType,
    open,
    schema,
    defaultValues: DEFAULT_VALUES,
    toFormValues,
    createMutationOptions: createEmployeeRoleTypeMutation(),
    updateMutationOptions: updateEmployeeRoleTypeMutation(),
    buildCreateVars: (values) => ({ body: toBody(values) }),
    buildUpdateVars: (values, r) => ({
      path: { role_type_id: r.id },
      body: toBody(values),
    }),
    invalidateKeys: (r) =>
      r
        ? [
            listEmployeeRoleTypesQueryKey(),
            getEmployeeRoleTypeQueryKey({ path: { role_type_id: r.id } }),
          ]
        : [listEmployeeRoleTypesQueryKey()],
    entityLabel: "Employee Role Type",
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
            {isEdit ? "Edit Employee Role Type" : "Add Employee Role Type"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Field data-invalid={!!errors.name}>
            <FieldLabel htmlFor="ert-name">Name</FieldLabel>
            <Input
              id="ert-name"
              aria-invalid={!!errors.name}
              {...register("name")}
            />
            <FieldError errors={[errors.name]} />
          </Field>

          <Field data-invalid={!!errors.description}>
            <FieldLabel htmlFor="ert-description">Description</FieldLabel>
            <Textarea
              id="ert-description"
              aria-invalid={!!errors.description}
              rows={3}
              {...register("description")}
            />
            <FieldError errors={[errors.description]} />
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
