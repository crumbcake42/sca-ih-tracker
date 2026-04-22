import { getRouteApi } from "@tanstack/react-router";
import { SchoolDetail } from "@/features/schools/components/SchoolDetail";

const routeApi = getRouteApi("/_authenticated/admin/schools/$schoolId");

export function SchoolDetailPage() {
  const { schoolId } = routeApi.useParams();
  return <SchoolDetail schoolId={schoolId} />;
}
