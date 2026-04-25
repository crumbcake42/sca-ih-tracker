import { queryClient } from "@/api/queryClient";
import { getWaCodeOptions } from "@/features/wa-codes/api/wa-codes";

export function prefetchWaCode(waCodeId: number) {
  return queryClient.ensureQueryData(
    getWaCodeOptions({ path: { identifier: String(waCodeId) } }),
  );
}
