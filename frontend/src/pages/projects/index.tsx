import { ProjectList } from "@/features/projects/components/ProjectList";
import { useUrlSearch } from "@/hooks/useUrlSearch";
import { useUrlPagination } from "@/hooks/useUrlPagination";

export function ProjectsListPage() {
  const [search, setSearch] = useUrlSearch("search");
  const { pagination, onPaginationChange } = useUrlPagination();

  return (
    <ProjectList
      search={search}
      onSearchChange={setSearch}
      pagination={pagination}
      onPaginationChange={onPaginationChange}
    />
  );
}
