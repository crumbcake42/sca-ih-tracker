import { useNavigate } from "@tanstack/react-router";
import type { School } from "@/api/generated/types.gen";
import { SchoolsList } from "@/features/schools/components/SchoolsList";
import { useUrlSearch } from "@/hooks/useUrlSearch";
import { useUrlPagination } from "@/hooks/useUrlPagination";

export function SchoolsListPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useUrlSearch("search");
  const { pagination, onPaginationChange } = useUrlPagination();

  function handleRowClick(school: School) {
    void navigate({
      to: "/admin/schools/$schoolId",
      params: { schoolId: String(school.id) },
    });
  }

  return (
    <SchoolsList
      search={search}
      onSearchChange={setSearch}
      pagination={pagination}
      onPaginationChange={onPaginationChange}
      onRowClick={handleRowClick}
    />
  );
}
