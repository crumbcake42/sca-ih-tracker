import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import type { QueryKey, QueryFunction } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/DataTable";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { useUrlSearch } from "@/hooks/useUrlSearch";
import { useUrlPagination } from "@/hooks/useUrlPagination";

/** Minimal paginated shape that all list endpoints must satisfy. */
export interface Paginated<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

interface EntityListPageProps<
  T,
  TPageData extends Paginated<T> = Paginated<T>,
> {
  title: string;
  columns: ColumnDef<T>[];
  /**
   * Factory that produces UseQueryOptions given search/pagination params.
   * Pass `listXxxOptions` directly. TypeScript infers `TPageData` from the factory's
   * return type, which must extend `Paginated<T>`.
   */
  queryOptions: (options?: {
    query?: { search?: string | null; skip?: number; limit?: number };
  }) => {
    queryKey: QueryKey;
    queryFn?: QueryFunction<TPageData, never, never>;
  };
  searchPlaceholder?: string;
  emptyMessage?: string;
  /** Right-side header slot: Add / Import buttons, etc. */
  actions?: ReactNode;
  onRowClick?: (row: T) => void;
}

/**
 * Generic admin list page: owns URL-synced search + pagination, runs the list
 * query, and renders a Card-wrapped DataTable with a header (title + search +
 * actions slot). Columns and query options are entity-specific.
 */
export function EntityListPage<
  T,
  TPageData extends Paginated<T> = Paginated<T>,
>({
  title,
  columns,
  queryOptions,
  searchPlaceholder = "Search…",
  emptyMessage = "No results found.",
  actions,
  onRowClick,
}: EntityListPageProps<T, TPageData>) {
  const [search, setSearch] = useUrlSearch("search");
  const { pagination, onPaginationChange } = useUrlPagination();

  const { skip, limit } = {
    skip: pagination.pageIndex * pagination.pageSize,
    limit: pagination.pageSize,
  };

  const opts = queryOptions({
    query: { search: search || undefined, skip, limit },
  });
  const { data, isLoading, error } = useQuery<TPageData>({
    queryKey: opts.queryKey,
    queryFn: opts.queryFn as QueryFunction<TPageData>,
  });

  const pageCount = data ? Math.ceil(data.total / data.limit) : 1;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{title}</h1>
        <div className="flex items-center gap-2">
          <Input
            placeholder={searchPlaceholder}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-56"
          />
          {actions}
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <DataTable
            columns={columns}
            data={data?.items ?? []}
            pagination={pagination}
            onPaginationChange={onPaginationChange}
            pageCount={pageCount}
            isLoading={isLoading}
            error={error}
            emptyMessage={emptyMessage}
            onRowClick={onRowClick}
          />
        </CardContent>
      </Card>
    </div>
  );
}
