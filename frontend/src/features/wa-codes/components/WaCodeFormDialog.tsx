import { Controller } from "react-hook-form";
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import type {
  WaCode,
  WaCodeLevel,
  WaCodeConnections,
} from "@/api/generated/types.gen";
import { useEntityForm } from "@/hooks/useEntityForm";
import {
  createWaCodeMutation,
  updateWaCodeMutation,
  listWaCodesQueryKey,
  getWaCodeQueryKey,
  getWaCodeConnectionsOptions,
} from "@/features/wa-codes/api/wa-codes";

const LEVEL_OPTIONS: readonly WaCodeLevel[] = ["project", "building"];

const schema = z.object({
  code: z.string().min(1, "Code is required."),
  description: z.string().min(1, "Description is required."),
  level: z.enum(LEVEL_OPTIONS as [WaCodeLevel, ...WaCodeLevel[]]),
  default_fee: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const DEFAULT_VALUES: FormValues = {
  code: "",
  description: "",
  level: "project",
};

function toFormValues(waCode: WaCode): FormValues {
  return {
    code: waCode.code,
    description: waCode.description,
    level: waCode.level,
    default_fee: waCode.default_fee ?? "",
  };
}

function toBody(values: FormValues) {
  return {
    code: values.code,
    description: values.description,
    level: values.level,
    default_fee: values.default_fee || null,
  };
}

function hasConnections(data: WaCodeConnections | undefined): boolean {
  if (!data) return false;
  return Object.values(data).some((v) => v > 0);
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  waCode?: WaCode;
}

export function WaCodeFormDialog({ open, onOpenChange, waCode }: Props) {
  const isEdit = !!waCode;

  const { data: connectionsData } = useQuery({
    ...getWaCodeConnectionsOptions({ path: { wa_code_id: waCode?.id ?? 0 } }),
    enabled: isEdit && open,
  });

  const levelLocked = isEdit && hasConnections(connectionsData);

  const { form, onSubmit, isPending } = useEntityForm({
    entity: waCode,
    open,
    schema,
    defaultValues: DEFAULT_VALUES,
    toFormValues,
    createMutationOptions: createWaCodeMutation(),
    updateMutationOptions: updateWaCodeMutation(),
    buildCreateVars: (values) => ({ body: toBody(values) }),
    buildUpdateVars: (values, wc) => ({
      path: { wa_code_id: wc.id },
      body: toBody(values),
    }),
    invalidateKeys: (wc) =>
      wc
        ? [
            listWaCodesQueryKey(),
            getWaCodeQueryKey({ path: { identifier: String(wc.id) } }),
          ]
        : [listWaCodesQueryKey()],
    entityLabel: "WA Code",
    onSuccess: () => onOpenChange(false),
  });

  const {
    register,
    control,
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
          <DialogTitle>{isEdit ? "Edit WA Code" : "Add WA Code"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Field data-invalid={!!errors.code}>
            <FieldLabel htmlFor="wac-code">Code</FieldLabel>
            <Input
              id="wac-code"
              className="font-mono"
              aria-invalid={!!errors.code}
              {...register("code")}
            />
            <FieldError errors={[errors.code]} />
          </Field>

          <Field data-invalid={!!errors.description}>
            <FieldLabel htmlFor="wac-description">Description</FieldLabel>
            <Textarea
              id="wac-description"
              rows={3}
              aria-invalid={!!errors.description}
              {...register("description")}
            />
            <FieldError errors={[errors.description]} />
          </Field>

          <Field data-invalid={!!errors.level}>
            <FieldLabel htmlFor="wac-level">Level</FieldLabel>
            <Controller
              control={control}
              name="level"
              render={({ field }) => (
                <Select
                  value={field.value}
                  onValueChange={field.onChange}
                  disabled={levelLocked}
                >
                  <SelectTrigger
                    id="wac-level"
                    className="w-full"
                    aria-invalid={!!errors.level}
                  >
                    <SelectValue placeholder="Select level…" />
                  </SelectTrigger>
                  <SelectContent>
                    {LEVEL_OPTIONS.map((l) => (
                      <SelectItem key={l} value={l}>
                        {l.charAt(0).toUpperCase() + l.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {levelLocked && (
              <p className="text-xs text-muted-foreground">
                In use — level locked.
              </p>
            )}
            <FieldError errors={[errors.level]} />
          </Field>

          <Field data-invalid={!!errors.default_fee}>
            <FieldLabel htmlFor="wac-default-fee">Default fee</FieldLabel>
            <Input
              id="wac-default-fee"
              placeholder="Optional (e.g. 150.00)"
              {...register("default_fee")}
            />
            <FieldError errors={[errors.default_fee]} />
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
