import { queryClient } from "@/api/queryClient";
import { getEmployeeOptions } from "@/features/employees/api/employees";

export function prefetchEmployee(employeeId: number) {
  return queryClient.ensureQueryData(
    getEmployeeOptions({ path: { employee_id: employeeId } }),
  );
}
