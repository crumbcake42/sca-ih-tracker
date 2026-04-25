import { queryClient } from "@/api/queryClient";
import { getContractorOptions } from "@/features/contractors/api/contractors";

export function prefetchContractor(contractorId: number) {
  return queryClient.ensureQueryData(
    getContractorOptions({ path: { contractor_id: contractorId } }),
  );
}
