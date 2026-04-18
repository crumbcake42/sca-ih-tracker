import { useNavigate, useSearch } from '@tanstack/react-router'
import type { OnChangeFn, PaginationState } from '@tanstack/react-table'

/**
 * Syncs TanStack Table pagination state with `page` / `pageSize` URL search params.
 * The route's validateSearch schema must include these params (or use strict: false reads).
 */
export function useUrlPagination(defaultPageSize = 20) {
  const navigate = useNavigate()
  const search = useSearch({ strict: false })

  const pagination: PaginationState = {
    pageIndex: Math.max(0, Number(search.page ?? 1) - 1),
    pageSize: search.pageSize ? Number(search.pageSize) : defaultPageSize,
  }

  const onPaginationChange: OnChangeFn<PaginationState> = (updater) => {
    const next = typeof updater === 'function' ? updater(pagination) : updater
    void navigate({
      search: ((prev: Record<string, unknown>) => ({
        ...prev,
        page: next.pageIndex + 1,
        pageSize: next.pageSize !== defaultPageSize ? next.pageSize : undefined,
      })) as never,
    })
  }

  return { pagination, onPaginationChange }
}
