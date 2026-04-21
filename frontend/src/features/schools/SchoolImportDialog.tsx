import { useForm } from "react-hook-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Field, FieldLabel, FieldError } from "@/components/ui/field";
import {
  importBatchSchoolsBatchImportPostMutation,
  listEntriesSchoolsGetQueryKey,
} from "@/api/generated/@tanstack/react-query.gen";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface FormValues {
  file: FileList;
}

export function SchoolImportDialog({ open, onOpenChange }: Props) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<FormValues>();

  const { mutate, isPending } = useMutation({
    ...importBatchSchoolsBatchImportPostMutation(),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({
        queryKey: listEntriesSchoolsGetQueryKey(),
      });
      toast.success(`Imported ${data.created_items.length} school(s).`);
      reset();
      onOpenChange(false);
    },
    onError: () => {
      toast.error("Import failed. Check that the CSV format is correct.");
    },
  });

  const onSubmit = (values: FormValues) => {
    const file = values.file[0];
    if (!file) return;
    mutate({ body: { file } });
  };

  const handleOpenChange = (next: boolean) => {
    if (!next) reset();
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Import Schools from CSV</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Field data-invalid={!!errors.file}>
            <FieldLabel htmlFor="import-file">CSV file</FieldLabel>
            <input
              id="import-file"
              type="file"
              accept=".csv"
              className="block w-full text-sm"
              {...register("file", { required: "Please select a CSV file." })}
            />
            <FieldError errors={[errors.file]} />
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
              {isPending ? "Importing…" : "Import"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
