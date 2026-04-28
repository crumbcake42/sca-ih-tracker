import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { getProjectStatusOptions } from "@/features/projects/api/projects";

interface Props {
  projectId: number;
}

interface CountBadgeProps {
  label: string;
  count: number;
}

function CountBadge({ label, count }: CountBadgeProps) {
  return (
    <span className="flex items-center gap-1 text-xs text-muted-foreground">
      {label}
      <Badge variant={count > 0 ? "destructive" : "secondary"}>{count}</Badge>
    </span>
  );
}

export function ProjectStatusBadge({ projectId }: Props) {
  const { data, isLoading } = useQuery(
    getProjectStatusOptions({ path: { project_id: projectId } }),
  );

  if (isLoading) {
    return (
      <div className="flex items-center gap-3">
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-5 w-28" />
        <Skeleton className="h-5 w-28" />
        <Skeleton className="h-5 w-28" />
        <Skeleton className="h-5 w-32" />
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Badge variant="outline" className="capitalize">
        {data.status.replace(/_/g, " ")}
      </Badge>
      <CountBadge label="Pending RFAs" count={data.pending_rfa_count} />
      <CountBadge
        label="Outstanding deliverables"
        count={data.outstanding_deliverable_count}
      />
      <CountBadge
        label="Unconfirmed time entries"
        count={data.unconfirmed_time_entry_count}
      />
      <CountBadge
        label="Unfulfilled requirements"
        count={data.unfulfilled_requirement_count}
      />
    </div>
  );
}
