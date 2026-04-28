import { getRouteApi } from "@tanstack/react-router";
import { ProjectDetail } from "@/features/projects/components/ProjectDetail";

const routeApi = getRouteApi("/_authenticated/projects/$projectId");

export function ProjectDetailPage() {
  const { projectId } = routeApi.useParams();
  return <ProjectDetail projectId={Number(projectId)} />;
}
