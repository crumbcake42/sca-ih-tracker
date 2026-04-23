import type { Meta, StoryObj, Decorator } from "@storybook/react-vite";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import type { NoteRead } from "@/api/generated/types.gen";
import { listNotesQueryKey } from "@/features/notes/api/notes";
import { NotesPanel } from "./NotesPanel";

const ENTITY_TYPE = "project" as const;
const ENTITY_ID = 1;

const queryArgs = { path: { entity_type: ENTITY_TYPE, entity_id: ENTITY_ID } };

const manualNote: NoteRead = {
  id: 1,
  entity_type: ENTITY_TYPE,
  entity_id: ENTITY_ID,
  parent_note_id: null,
  body: "Reviewed all samples — looks good.",
  note_type: null,
  is_blocking: false,
  is_resolved: false,
  resolved_by_id: null,
  resolved_at: null,
  created_at: "2025-04-01T10:00:00Z",
  updated_at: "2025-04-01T10:00:00Z",
  created_by_id: 2,
  updated_by_id: null,
  replies: [
    {
      id: 3,
      entity_type: ENTITY_TYPE,
      entity_id: ENTITY_ID,
      parent_note_id: 1,
      body: "Confirmed, closing this out.",
      note_type: null,
      is_blocking: false,
      is_resolved: false,
      resolved_by_id: null,
      resolved_at: null,
      created_at: "2025-04-02T09:00:00Z",
      updated_at: "2025-04-02T09:00:00Z",
      created_by_id: 3,
      updated_by_id: null,
      replies: [],
    },
  ],
};

const systemNote: NoteRead = {
  id: 2,
  entity_type: ENTITY_TYPE,
  entity_id: ENTITY_ID,
  parent_note_id: null,
  body: "Time entry conflict detected between entries #4 and #7.",
  note_type: "time_entry_conflict",
  is_blocking: true,
  is_resolved: false,
  resolved_by_id: null,
  resolved_at: null,
  created_at: "2025-04-01T08:00:00Z",
  updated_at: "2025-04-01T08:00:00Z",
  created_by_id: 1,
  updated_by_id: null,
  replies: [],
};

const resolvedNote: NoteRead = {
  id: 4,
  entity_type: ENTITY_TYPE,
  entity_id: ENTITY_ID,
  parent_note_id: null,
  body: "Missing WA code for asbestos samples.",
  note_type: null,
  is_blocking: true,
  is_resolved: true,
  resolved_by_id: 2,
  resolved_at: "2025-04-03T11:00:00Z",
  created_at: "2025-03-30T14:00:00Z",
  updated_at: "2025-04-03T11:00:00Z",
  created_by_id: 2,
  updated_by_id: 2,
  replies: [],
};

function withNotes(notes: NoteRead[]): Decorator {
  return (Story) => {
    const queryClient = useQueryClient();
    useEffect(() => {
      queryClient.setQueryData(listNotesQueryKey(queryArgs), notes);
    }, [queryClient]);
    return <Story />;
  };
}

const meta: Meta<typeof NotesPanel> = {
  title: "Features/NotesPanel",
  component: NotesPanel,
  args: { entityType: ENTITY_TYPE, entityId: ENTITY_ID },
};

export default meta;
type Story = StoryObj<typeof NotesPanel>;

export const Populated: Story = {
  decorators: [withNotes([systemNote, manualNote, resolvedNote])],
};

export const Empty: Story = {
  decorators: [withNotes([])],
};
