import { getRouteApi } from "@tanstack/react-router";
import { HygienistDetail } from "@/features/hygienists/components/HygienistDetail";

const routeApi = getRouteApi("/_authenticated/admin/hygienists/$hygienistId");

export function HygienistDetailPage() {
  const { hygienistId } = routeApi.useParams();
  return <HygienistDetail hygienistId={Number(hygienistId)} />;
}
