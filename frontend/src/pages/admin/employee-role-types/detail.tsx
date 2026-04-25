import { getRouteApi } from "@tanstack/react-router";
import { EmployeeRoleTypeDetail } from "@/features/employee-role-types/components/EmployeeRoleTypeDetail";

const routeApi = getRouteApi(
  "/_authenticated/admin/employee-role-types/$roleTypeId",
);

export function EmployeeRoleTypeDetailPage() {
  const { roleTypeId } = routeApi.useParams();
  return <EmployeeRoleTypeDetail roleTypeId={Number(roleTypeId)} />;
}
