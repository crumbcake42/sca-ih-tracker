import { createFileRoute } from "@tanstack/react-router";
import { prefetchEmployee } from "@/pages/admin/employees/loader";
import { EmployeeDetailPage } from "@/pages/admin/employees/detail";

export const Route = createFileRoute(
  "/_authenticated/admin/employees/$employeeId",
)({
  loader: ({ params }) => prefetchEmployee(Number(params.employeeId)),
  component: EmployeeDetailPage,
});
