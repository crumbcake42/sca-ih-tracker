import { getRouteApi } from "@tanstack/react-router";
import { WaCodeDetail } from "@/features/wa-codes/components/WaCodeDetail";

const routeApi = getRouteApi("/_authenticated/admin/wa-codes/$waCodeId");

export function WaCodeDetailPage() {
  const { waCodeId } = routeApi.useParams();
  return <WaCodeDetail waCodeId={Number(waCodeId)} />;
}
