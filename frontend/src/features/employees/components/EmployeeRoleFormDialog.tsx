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
import type { EmployeeRole, EmployeeRoleType } from "@/api/generated/types.gen";
import { applyServerErrors } from "@/lib/form-errors";
import {
  createEmployeeRoleMutation,
  updateEmployeeRoleMutation,
  listEmployeeRolesQueryKey,
} from "@/features/employees/api/employees";
import { EMPLOYEE_ROLE_TYPES } from "@/features/employees/api/employeeRoleTypes";

const schema = z.object({
  role_type: z.string().min(1, "Role type is required."),
  start_date: z.string().min(1, "Start date is required."),
  end_date: z.string().optional(),
  hourly_rate: z
    .string()
    .min(1, "Hourly rate is required.")
    .refine((v) => !isNaN(parseFloat(v)) && parseFloat(v) > 0, {
      message: "Must be a positive number.",
    }),
});

type FormValues = z.infer<typeof schema>;

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  employeeId: number;
  role?: EmployeeRole;
}

function get409Detail(err: unknown): string | null {
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

function toFormValues(role: EmployeeRole): FormValues {
  return {
    role_type: role.role_type,
    start_date: role.start_date,
    end_date: role.end_date ?? "",
    hourly_rate: String(role.hourly_rate),
  };
}

const DEFAULT_VALUES: FormValues = {
  role_type: "",
  start_date: "",
  end_date: "",
  hourly_rate: "",
};

/** Dialog for creating or editing a single employee role. In edit mode, role_type and start_date are immutable. */
export function EmployeeRoleFormDialog({
  open,
  onOpenChange,
  employeeId,
  role,
}: Props) {
  const queryClient = useQueryClient();
  const isEdit = !!role;

  const {
    register,
    handleSubmit,
    control,
    reset,
    setError,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: standardSchemaResolver(schema),
    defaultValues: role ? toFormValues(role) : DEFAULT_VALUES,
  });

  useEffect(() => {
    if (open) {
      reset(role ? toFormValues(role) : DEFAULT_VALUES);
    }
  }, [open, role, reset]);

  const invalidateRoles = () => {
    void queryClient.invalidateQueries({
      queryKey: listEmployeeRolesQueryKey({
        path: { employee_id: employeeId },
      }),
    });
  };

  const handleError = (err: unknown) => {
    const detail = get409Detail(err);
    if (detail) {
      setError("root.serverError", { message: detail });
      return;
    }
    if (!applyServerErrors(err, setError)) {
      toast.error("Could not save role.");
    }
  };

  const { mutate: createRole, isPending: isCreating } = useMutation({
    ...createEmployeeRoleMutation(),
    onSuccess: () => {
      invalidateRoles();
      toast.success("Role added.");
      onOpenChange(false);
    },
    onError: handleError,
  });

  const { mutate: updateRole, isPending: isUpdating } = useMutation({
    ...updateEmployeeRoleMutation(),
    onSuccess: () => {
      invalidateRoles();
      toast.success("Role updated.");
      onOpenChange(false);
    },
    onError: handleError,
  });

  const isPending = isCreating || isUpdating;

  const onSubmit = (values: FormValues) => {
    if (isEdit && role) {
      updateRole({
        path: { role_id: role.id },
        body: {
          end_date: values.end_date || null,
          hourly_rate: values.hourly_rate,
        },
      });
    } else {
      createRole({
        path: { employee_id: employeeId },
        body: {
          role_type: values.role_type as EmployeeRoleType,
          start_date: values.start_date,
          end_date: values.end_date || null,
          hourly_rate: values.hourly_rate,
        },
      });
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
          <DialogTitle>{isEdit ? "Edit Role" : "Add Role"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {errors.root?.serverError && (
            <p
              role="alert"
              className="rounded-none border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
            >
              {errors.root.serverError.message}
            </p>
          )}

          <Field data-invalid={!!errors.role_type}>
            <FieldLabel htmlFor="role-type">Role type</FieldLabel>
            <Controller
              control={control}
              name="role_type"
              render={({ field }) => (
                <Select
                  value={field.value}
                  onValueChange={field.onChange}
                  disabled={isEdit}
                >
                  <SelectTrigger
                    id="role-type"
                    className="w-full"
                    aria-invalid={!!errors.role_type}
                    data-testid="role-type-trigger"
                  >
                    <SelectValue placeholder="Select role type…" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.values(EMPLOYEE_ROLE_TYPES).map((type) => (
                      <SelectItem key={type} value={type}>
                        {type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            <FieldError errors={[errors.role_type]} />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field data-invalid={!!errors.start_date}>
              <FieldLabel htmlFor="role-start-date">Start date</FieldLabel>
              <Input
                id="role-start-date"
                type="date"
                disabled={isEdit}
                aria-invalid={!!errors.start_date}
                {...register("start_date")}
              />
              <FieldError errors={[errors.start_date]} />
            </Field>

            <Field data-invalid={!!errors.end_date}>
              <FieldLabel htmlFor="role-end-date">End date</FieldLabel>
              <Input
                id="role-end-date"
                type="date"
                aria-invalid={!!errors.end_date}
                {...register("end_date")}
              />
              <FieldError errors={[errors.end_date]} />
            </Field>
          </div>

          <Field data-invalid={!!errors.hourly_rate}>
            <FieldLabel htmlFor="role-hourly-rate">Hourly rate ($)</FieldLabel>
            <Input
              id="role-hourly-rate"
              type="number"
              step="0.01"
              min="0"
              aria-invalid={!!errors.hourly_rate}
              {...register("hourly_rate")}
            />
            <FieldError errors={[errors.hourly_rate]} />
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
              {isPending ? "Saving…" : isEdit ? "Save changes" : "Add role"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
