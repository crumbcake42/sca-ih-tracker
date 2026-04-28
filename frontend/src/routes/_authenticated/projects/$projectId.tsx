import { createFileRoute } from "@tanstack/react-router";
import { prefetchProject } from "@/pages/projects/loader";
import { ProjectDetailPage } from "@/pages/projects/detail";

export const Route = createFileRoute("/_authenticated/projects/$projectId")({
  loader: ({ params }) => prefetchProject(Number(params.projectId)),
  component: ProjectDetailPage,
});
