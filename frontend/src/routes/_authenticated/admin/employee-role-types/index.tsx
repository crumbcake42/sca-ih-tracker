import { createFileRoute } from "@tanstack/react-router";
import { EmployeeRoleTypeListPage } from "@/pages/admin/employee-role-types";

export const Route = createFileRoute(
  "/_authenticated/admin/employee-role-types/",
)({
  component: EmployeeRoleTypeListPage,
});
