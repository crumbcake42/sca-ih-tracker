import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { ArrowLeftIcon } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getProjectOptions,
  getProjectStatusOptions,
} from "@/features/projects/api/projects";
import { ProjectStatusBadge } from "@/features/projects/status/ProjectStatusBadge";
import { CloseProjectDialog } from "@/features/projects/close/CloseProjectDialog";

interface Props {
  projectId: number;
}

function DetailRow({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  return (
    <div className="flex items-baseline gap-4 border-b py-2 last:border-0">
      <dt className="w-36 shrink-0 text-sm text-muted-foreground">{label}</dt>
      <dd className="text-sm">{value ?? "—"}</dd>
    </div>
  );
}

export function ProjectDetail({ projectId }: Props) {
  const [closeOpen, setCloseOpen] = useState(false);

  const {
    data: project,
    isLoading,
    error,
  } = useQuery(getProjectOptions({ path: { project_id: projectId } }));

  const { data: status } = useQuery(
    getProjectStatusOptions({ path: { project_id: projectId } }),
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/projects">
            <ArrowLeftIcon size={15} />
            Projects
          </Link>
        </Button>
        {project && <h1 className="text-2xl font-semibold">{project.name}</h1>}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <ProjectStatusBadge projectId={projectId} />
        {status?.status !== "locked" && (
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setCloseOpen(true)}
          >
            Close project
          </Button>
        )}
      </div>

      <Card className="max-w-lg">
        <CardContent className="pt-4">
          {isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-6 w-full" />
              ))}
            </div>
          )}
          {error && (
            <p className="text-sm text-destructive">
              Could not load project details.
            </p>
          )}
          {project && (
            <dl>
              <DetailRow label="Name" value={project.name} />
              <DetailRow
                label="Project number"
                value={project.project_number}
              />
              <DetailRow
                label="Schools"
                value={project.school_ids?.length ?? 0}
              />
            </dl>
          )}
        </CardContent>
      </Card>

      <CloseProjectDialog
        open={closeOpen}
        onOpenChange={setCloseOpen}
        projectId={projectId}
      />
    </div>
  );
}
