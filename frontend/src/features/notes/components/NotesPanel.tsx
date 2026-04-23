import { useQuery } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import type { NoteEntityType } from "@/api/generated/types.gen";
import { listNotesOptions } from "@/features/notes/api/notes";
import { NoteComposer } from "@/features/notes/components/NoteComposer";
import { NoteItem } from "@/features/notes/components/NoteItem";

interface Props {
  entityType: NoteEntityType;
  entityId: number;
}

/** Polymorphic notes panel — renders notes for any entity type. */
export function NotesPanel({ entityType, entityId }: Props) {
  const { data, isPending, isError } = useQuery(
    listNotesOptions({
      path: { entity_type: entityType, entity_id: entityId },
    }),
  );

  return (
    <div className="space-y-4">
      <NoteComposer entityType={entityType} entityId={entityId} />

      {isPending && (
        <div className="space-y-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      )}

      {isError && (
        <p className="text-sm text-destructive">Failed to load notes.</p>
      )}

      {data && data.length === 0 && (
        <p className="text-sm text-muted-foreground">No notes yet.</p>
      )}

      {data && data.length > 0 && (
        <div className="space-y-3">
          {data.map((note) => (
            <NoteItem
              key={note.id}
              note={note}
              entityType={entityType}
              entityId={entityId}
            />
          ))}
        </div>
      )}
    </div>
  );
}
