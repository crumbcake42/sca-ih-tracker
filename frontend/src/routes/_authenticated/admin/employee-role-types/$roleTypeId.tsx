import { createFileRoute } from "@tanstack/react-router";
import { prefetchEmployeeRoleType } from "@/pages/admin/employee-role-types/loader";
import { EmployeeRoleTypeDetailPage } from "@/pages/admin/employee-role-types/detail";

export const Route = createFileRoute(
  "/_authenticated/admin/employee-role-types/$roleTypeId",
)({
  loader: ({ params }) => prefetchEmployeeRoleType(Number(params.roleTypeId)),
  component: EmployeeRoleTypeDetailPage,
});
