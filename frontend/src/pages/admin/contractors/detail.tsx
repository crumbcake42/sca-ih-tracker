import { getRouteApi } from "@tanstack/react-router";
import { ContractorDetail } from "@/features/contractors/components/ContractorDetail";

const routeApi = getRouteApi("/_authenticated/admin/contractors/$contractorId");

export function ContractorDetailPage() {
  const { contractorId } = routeApi.useParams();
  return <ContractorDetail contractorId={Number(contractorId)} />;
}
