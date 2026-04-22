import { createFileRoute } from "@tanstack/react-router";
import { prefetchSchool } from "@/pages/admin/schools/loader";
import { SchoolDetailPage } from "@/pages/admin/schools/detail";

export const Route = createFileRoute("/_authenticated/admin/schools/$schoolId")(
  {
    loader: ({ params }) => prefetchSchool(params.schoolId),
    component: SchoolDetailPage,
  },
);
