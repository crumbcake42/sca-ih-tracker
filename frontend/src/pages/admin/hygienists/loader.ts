import { queryClient } from "@/api/queryClient";
import { getHygienistOptions } from "@/features/hygienists/api/hygienists";

export function prefetchHygienist(hygienistId: number) {
  return queryClient.ensureQueryData(
    getHygienistOptions({ path: { hygienist_id: hygienistId } }),
  );
}
