import { createFileRoute } from "@tanstack/react-router";
import { queryClient } from "../../../../api/queryClient";
import { getSchoolSchoolsIdentifierGetOptions } from "../../../../api/generated/@tanstack/react-query.gen";
import { SchoolDetailPage } from "../../../../features/schools/SchoolDetailPage";

export const Route = createFileRoute("/_authenticated/admin/schools/$schoolId")(
  {
    loader: ({ params }) =>
      queryClient.ensureQueryData(
        getSchoolSchoolsIdentifierGetOptions({
          path: { identifier: params.schoolId },
        }),
      ),
    component: SchoolDetailRoute,
  },
);

function SchoolDetailRoute() {
  const { schoolId } = Route.useParams();
  return <SchoolDetailPage schoolId={schoolId} />;
}
