import { queryClient } from "@/api/queryClient";
import {
  getProjectOptions,
  getProjectStatusOptions,
} from "@/features/projects/api/projects";

export function prefetchProject(projectId: number) {
  return Promise.all([
    queryClient.ensureQueryData(
      getProjectOptions({ path: { project_id: projectId } }),
    ),
    queryClient.ensureQueryData(
      getProjectStatusOptions({ path: { project_id: projectId } }),
    ),
  ]);
}
