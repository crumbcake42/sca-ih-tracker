import { queryClient } from "@/api/queryClient";
import { getEmployeeRoleTypeOptions } from "@/features/employee-role-types/api/employeeRoleTypes";

export function prefetchEmployeeRoleType(roleTypeId: number) {
  return queryClient.ensureQueryData(
    getEmployeeRoleTypeOptions({ path: { role_type_id: roleTypeId } }),
  );
}
