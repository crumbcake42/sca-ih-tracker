import { useState } from "react";
import { useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  ChatCircleIcon,
  CheckCircleIcon,
  CaretDownIcon,
  CaretRightIcon,
} from "@phosphor-icons/react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Field, FieldLabel, FieldError } from "@/components/ui/field";
import { cn } from "@/lib/utils";
import type { NoteRead, NoteEntityType } from "@/api/generated/types.gen";
import {
  createNoteReplyMutation,
  listNotesQueryKey,
} from "@/features/notes/api/notes";
import { ResolveNoteDialog } from "@/features/notes/components/ResolveNoteDialog";

const replySchema = z.object({
  body: z.string().min(1, "Reply body is required."),
});

type ReplyFormValues = z.infer<typeof replySchema>;

interface ReplyFormProps {
  noteId: number;
  entityType: NoteEntityType;
  entityId: number;
  onDone: () => void;
}

function ReplyForm({ noteId, entityType, entityId, onDone }: ReplyFormProps) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ReplyFormValues>({
    resolver: standardSchemaResolver(replySchema),
    defaultValues: { body: "" },
  });

  const { mutate, isPending } = useMutation({
    ...createNoteReplyMutation(),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: listNotesQueryKey({
          path: { entity_type: entityType, entity_id: entityId },
        }),
      });
      toast.success("Reply added.");
      reset();
      onDone();
    },
    onError: () => {
      toast.error("Could not add reply.");
    },
  });

  const onSubmit = (values: ReplyFormValues) => {
    mutate({ path: { note_id: noteId }, body: { body: values.body } });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="mt-2 space-y-2">
      <Field data-invalid={!!errors.body}>
        <FieldLabel htmlFor={`reply-body-${noteId}`} className="sr-only">
          Reply
        </FieldLabel>
        <Textarea
          id={`reply-body-${noteId}`}
          placeholder="Write a reply…"
          aria-invalid={!!errors.body}
          {...register("body")}
        />
        <FieldError errors={[errors.body]} />
      </Field>
      <div className="flex justify-end gap-2">
        <Button type="button" size="sm" variant="outline" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" size="sm" disabled={isPending}>
          {isPending ? "Replying…" : "Reply"}
        </Button>
      </div>
    </form>
  );
}

interface Props {
  note: NoteRead;
  entityType: NoteEntityType;
  entityId: number;
  /** When true renders as a nested reply row (reduced chrome). */
  isReply?: boolean;
}

/** Single note row with badges, actions, reply form, and nested replies. */
export function NoteItem({
  note,
  entityType,
  entityId,
  isReply = false,
}: Props) {
  const [showReplyForm, setShowReplyForm] = useState(false);
  const [showReplies, setShowReplies] = useState(false);
  const [resolveOpen, setResolveOpen] = useState(false);

  const isSystem = note.note_type !== null;
  const isResolved = note.is_resolved;
  const replyCount = note.replies?.length ?? 0;

  const formattedDate = new Date(note.created_at).toLocaleDateString(
    undefined,
    {
      month: "short",
      day: "numeric",
      year: "numeric",
    },
  );

  return (
    <div className={cn("space-y-1", isReply && "ml-6 border-l pl-4")}>
      <div
        className={cn(
          "rounded border bg-card p-3 text-sm",
          isResolved && "opacity-60",
        )}
      >
        {/* Header row */}
        <div className="mb-1.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
          <span>{formattedDate}</span>
          {isSystem && (
            <Badge variant="secondary" className="text-[10px]">
              auto
            </Badge>
          )}
          {note.is_blocking && !isResolved && (
            <Badge variant="destructive" className="text-[10px]">
              blocking
            </Badge>
          )}
          {isResolved && (
            <Badge variant="outline" className="text-[10px]">
              resolved
            </Badge>
          )}
        </div>

        {/* Body */}
        <p
          className={cn(
            "whitespace-pre-wrap",
            isResolved && "line-through decoration-muted-foreground/50",
          )}
        >
          {note.body}
        </p>

        {/* Resolution note */}
        {isResolved && note.resolved_at && (
          <p className="mt-1 text-xs text-muted-foreground">
            Resolved {new Date(note.resolved_at).toLocaleDateString()}
          </p>
        )}

        {/* Action row — hidden for resolved notes and nested replies */}
        {!isResolved && !isReply && (
          <div className="mt-2 flex gap-2">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="h-6 px-2 text-xs"
              onClick={() => setShowReplyForm((v) => !v)}
            >
              <ChatCircleIcon size={12} className="mr-1" />
              Reply
            </Button>
            {!isSystem && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="h-6 px-2 text-xs"
                onClick={() => setResolveOpen(true)}
              >
                <CheckCircleIcon size={12} className="mr-1" />
                Resolve
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Inline reply form */}
      {showReplyForm && (
        <ReplyForm
          noteId={note.id}
          entityType={entityType}
          entityId={entityId}
          onDone={() => setShowReplyForm(false)}
        />
      )}

      {/* Replies disclosure */}
      {replyCount > 0 && (
        <div>
          <button
            type="button"
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            onClick={() => setShowReplies((v) => !v)}
          >
            {showReplies ? (
              <CaretDownIcon size={12} />
            ) : (
              <CaretRightIcon size={12} />
            )}
            {replyCount} {replyCount === 1 ? "reply" : "replies"}
          </button>
          {showReplies && (
            <div className="mt-1 space-y-1">
              {note.replies!.map((reply) => (
                <NoteItem
                  key={reply.id}
                  note={reply}
                  entityType={entityType}
                  entityId={entityId}
                  isReply
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Resolve dialog */}
      <ResolveNoteDialog
        noteId={note.id}
        entityType={entityType}
        entityId={entityId}
        open={resolveOpen}
        onOpenChange={setResolveOpen}
      />
    </div>
  );
}
