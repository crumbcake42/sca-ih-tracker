import { queryClient } from "@/api/queryClient";
import { getSchoolOptions } from "@/features/schools/api/schools";

export function prefetchSchool(schoolId: string) {
  return queryClient.ensureQueryData(
    getSchoolOptions({ path: { identifier: schoolId } }),
  );
}
