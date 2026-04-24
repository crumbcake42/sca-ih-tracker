import { getRouteApi } from "@tanstack/react-router";
import { EmployeeDetail } from "@/features/employees/components/EmployeeDetail";

const routeApi = getRouteApi("/_authenticated/admin/employees/$employeeId");

export function EmployeeDetailPage() {
  const { employeeId } = routeApi.useParams();
  return <EmployeeDetail employeeId={Number(employeeId)} />;
}
