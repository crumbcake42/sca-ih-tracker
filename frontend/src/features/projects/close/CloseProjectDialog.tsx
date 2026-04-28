import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import type {
  CloseProjectConflictDetail,
  BlockingIssue,
  UnfulfilledRequirement,
} from "@/api/generated/types.gen";
import {
  closeProjectMutation,
  getProjectStatusQueryKey,
  listProjectsQueryKey,
} from "@/features/projects/api/projects";

function parseCloseConflictDetail(
  err: unknown,
): CloseProjectConflictDetail | null {
  if (typeof err !== "object" || err === null) return null;
  const e = err as Record<string, unknown>;
  if (
    Array.isArray(e.blocking_issues) ||
    Array.isArray(e.unfulfilled_requirements)
  ) {
    return e as CloseProjectConflictDetail;
  }
  return null;
}

function groupBy<T>(items: T[], key: (item: T) => string): Map<string, T[]> {
  const map = new Map<string, T[]>();
  for (const item of items) {
    const k = key(item);
    const existing = map.get(k);
    if (existing) {
      existing.push(item);
    } else {
      map.set(k, [item]);
    }
  }
  return map;
}

function BlockingIssueList({ issues }: { issues: BlockingIssue[] }) {
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-destructive">
        This project has unresolved blocking notes:
      </p>
      <ul className="space-y-1">
        {issues.map((issue) => (
          <li key={issue.note_id} className="text-sm">
            <a
              href={issue.link}
              className="font-medium text-primary underline underline-offset-2 hover:no-underline"
            >
              {issue.entity_label}
            </a>
            {" — "}
            {issue.body}
          </li>
        ))}
      </ul>
    </div>
  );
}

function UnfulfilledRequirementList({
  requirements,
}: {
  requirements: UnfulfilledRequirement[];
}) {
  const grouped = groupBy(requirements, (r) => r.requirement_type);

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-destructive">
        This project has unfulfilled requirements:
      </p>
      {Array.from(grouped.entries()).map(([type, rows]) => (
        <div key={type}>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {type.replace(/_/g, " ")}
          </p>
          <ul className="space-y-1">
            {rows.map((req, i) => (
              <li key={i} className="flex items-center justify-between text-sm">
                <span>{req.label}</span>
                {req.is_dismissable && !req.is_dismissed && (
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled
                    title="Dismiss action coming in Session 2.5"
                  >
                    Dismiss
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: number;
}

export function CloseProjectDialog({ open, onOpenChange, projectId }: Props) {
  const queryClient = useQueryClient();
  const [conflict, setConflict] = useState<CloseProjectConflictDetail | null>(
    null,
  );

  const { mutate, isPending } = useMutation({
    ...closeProjectMutation(),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: getProjectStatusQueryKey({ path: { project_id: projectId } }),
      });
      void queryClient.invalidateQueries({ queryKey: listProjectsQueryKey() });
      toast.success("Project closed.");
      onOpenChange(false);
    },
    onError: (err) => {
      const detail = parseCloseConflictDetail(err);
      if (detail) {
        setConflict(detail);
      } else {
        toast.error("Could not close project.");
        onOpenChange(false);
      }
    },
  });

  const handleOpenChange = (next: boolean) => {
    if (!next) setConflict(null);
    onOpenChange(next);
  };

  const handleConfirm = () => {
    mutate({ path: { project_id: projectId } });
  };

  const hasBlockingIssues =
    conflict?.blocking_issues && conflict.blocking_issues.length > 0;
  const hasUnfulfilledRequirements =
    conflict?.unfulfilled_requirements &&
    conflict.unfulfilled_requirements.length > 0;
  const hasConflict = hasBlockingIssues || hasUnfulfilledRequirements;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Close project</DialogTitle>
        </DialogHeader>

        {!hasConflict && (
          <p className="text-sm text-muted-foreground">
            Close this project? All time entries and active batches will be
            locked.
          </p>
        )}

        {hasBlockingIssues && (
          <BlockingIssueList issues={conflict.blocking_issues!} />
        )}

        {hasUnfulfilledRequirements && !hasBlockingIssues && (
          <UnfulfilledRequirementList
            requirements={conflict.unfulfilled_requirements!}
          />
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={isPending}
            onClick={handleConfirm}
          >
            {isPending
              ? "Closing…"
              : hasConflict
                ? "Re-check"
                : "Close project"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
