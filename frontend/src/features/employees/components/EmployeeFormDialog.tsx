import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
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
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import type { Employee, TitleEnum } from "@/api/generated/types.gen";
import { applyServerErrors } from "@/lib/form-errors";
import {
  createEmployeeMutation,
  updateEmployeeMutation,
  listEmployeesQueryKey,
  getEmployeeQueryKey,
} from "@/features/employees/api/employees";

const TITLE_OPTIONS: readonly TitleEnum[] = ["Mr.", "Ms.", "Mrs."];

const schema = z.object({
  first_name: z.string().min(1, "First name is required."),
  last_name: z.string().min(1, "Last name is required."),
  display_name: z.string().optional(),
  title: z.enum(TITLE_OPTIONS as [TitleEnum, ...TitleEnum[]]).optional(),
  email: z
    .string()
    .email("Must be a valid email.")
    .optional()
    .or(z.literal("")),
  phone: z.string().optional(),
  adp_id: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  employee?: Employee;
}

function toFormValues(employee: Employee): FormValues {
  return {
    first_name: employee.first_name,
    last_name: employee.last_name,
    display_name: employee.display_name ?? "",
    title: employee.title ?? undefined,
    email: employee.email ?? "",
    phone: employee.phone ?? "",
    adp_id: employee.adp_id ?? "",
  };
}

export function EmployeeFormDialog({ open, onOpenChange, employee }: Props) {
  const queryClient = useQueryClient();
  const isEdit = !!employee;

  const {
    register,
    handleSubmit,
    control,
    reset,
    setError,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: standardSchemaResolver(schema),
    defaultValues: employee
      ? toFormValues(employee)
      : { first_name: "", last_name: "" },
  });

  useEffect(() => {
    if (open) {
      reset(
        employee ? toFormValues(employee) : { first_name: "", last_name: "" },
      );
    }
  }, [open, employee, reset]);

  const { mutate: createEmployee, isPending: isCreating } = useMutation({
    ...createEmployeeMutation(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: listEmployeesQueryKey() });
      toast.success("Employee created.");
      onOpenChange(false);
    },
    onError: (err) => {
      if (!applyServerErrors(err, setError)) {
        toast.error("Could not create employee.");
      }
    },
  });

  const { mutate: updateEmployee, isPending: isUpdating } = useMutation({
    ...updateEmployeeMutation(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: listEmployeesQueryKey() });
      if (employee) {
        void queryClient.invalidateQueries({
          queryKey: getEmployeeQueryKey({ path: { employee_id: employee.id } }),
        });
      }
      toast.success("Employee updated.");
      onOpenChange(false);
    },
    onError: (err) => {
      if (!applyServerErrors(err, setError)) {
        toast.error("Could not update employee.");
      }
    },
  });

  const isPending = isCreating || isUpdating;

  const onSubmit = (values: FormValues) => {
    const body = {
      first_name: values.first_name,
      last_name: values.last_name,
      display_name: values.display_name || null,
      title: values.title ?? null,
      email: values.email || null,
      phone: values.phone || null,
      adp_id: values.adp_id || null,
    };

    if (isEdit && employee) {
      updateEmployee({ path: { employee_id: employee.id }, body });
    } else {
      createEmployee({ body });
    }
  };

  const handleOpenChange = (next: boolean) => {
    if (!next) reset();
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit Employee" : "Add Employee"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Field data-invalid={!!errors.first_name}>
              <FieldLabel htmlFor="emp-first-name">First name</FieldLabel>
              <Input
                id="emp-first-name"
                aria-invalid={!!errors.first_name}
                {...register("first_name")}
              />
              <FieldError errors={[errors.first_name]} />
            </Field>
            <Field data-invalid={!!errors.last_name}>
              <FieldLabel htmlFor="emp-last-name">Last name</FieldLabel>
              <Input
                id="emp-last-name"
                aria-invalid={!!errors.last_name}
                {...register("last_name")}
              />
              <FieldError errors={[errors.last_name]} />
            </Field>
          </div>

          <Field data-invalid={!!errors.display_name}>
            <FieldLabel htmlFor="emp-display-name">Display name</FieldLabel>
            <Input
              id="emp-display-name"
              placeholder="Optional override for full name"
              {...register("display_name")}
            />
            <FieldError errors={[errors.display_name]} />
          </Field>

          <Field data-invalid={!!errors.title}>
            <FieldLabel htmlFor="emp-title">Title</FieldLabel>
            <Controller
              control={control}
              name="title"
              render={({ field }) => (
                <Select
                  value={field.value ?? ""}
                  onValueChange={(v) => field.onChange(v || undefined)}
                >
                  <SelectTrigger
                    id="emp-title"
                    className="w-full"
                    aria-invalid={!!errors.title}
                  >
                    <SelectValue placeholder="Select title…" />
                  </SelectTrigger>
                  <SelectContent>
                    {TITLE_OPTIONS.map((t) => (
                      <SelectItem key={t} value={t}>
                        {t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            <FieldError errors={[errors.title]} />
          </Field>

          <Field data-invalid={!!errors.email}>
            <FieldLabel htmlFor="emp-email">Email</FieldLabel>
            <Input
              id="emp-email"
              type="email"
              aria-invalid={!!errors.email}
              {...register("email")}
            />
            <FieldError errors={[errors.email]} />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field data-invalid={!!errors.phone}>
              <FieldLabel htmlFor="emp-phone">Phone</FieldLabel>
              <Input id="emp-phone" {...register("phone")} />
              <FieldError errors={[errors.phone]} />
            </Field>
            <Field data-invalid={!!errors.adp_id}>
              <FieldLabel htmlFor="emp-adp-id">ADP ID</FieldLabel>
              <Input
                id="emp-adp-id"
                className="font-mono"
                {...register("adp_id")}
              />
              <FieldError errors={[errors.adp_id]} />
            </Field>
          </div>

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
