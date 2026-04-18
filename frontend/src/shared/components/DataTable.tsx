import type {
  ColumnDef,
  OnChangeFn,
  PaginationState,
} from '@tanstack/react-table'
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { CaretLeftIcon, CaretRightIcon } from '@phosphor-icons/react'

import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

interface DataTableProps<TData> {
  columns: ColumnDef<TData>[]
  data: TData[]
  pagination: PaginationState
  onPaginationChange: OnChangeFn<PaginationState>
  /** Total number of pages (from API response). */
  pageCount: number
  isLoading?: boolean
  error?: unknown
  /** Called when a data row is clicked. */
  onRowClick?: (row: TData) => void
  emptyMessage?: string
  /** Number of skeleton rows to show while loading. */
  skeletonRows?: number
}

export function DataTable<TData>({
  columns,
  data,
  pagination,
  onPaginationChange,
  pageCount,
  isLoading = false,
  error,
  onRowClick,
  emptyMessage = 'No results.',
  skeletonRows = 5,
}: DataTableProps<TData>) {
  const table = useReactTable({
    data,
    columns,
    state: { pagination },
    onPaginationChange,
    pageCount,
    manualPagination: true,
    getCoreRowModel: getCoreRowModel(),
  })

  const colCount = columns.length
  const rows = table.getRowModel().rows
  const hasData = !isLoading && !error && rows.length > 0

  return (
    <div className="space-y-2">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((hg) => (
            <TableRow key={hg.id}>
              {hg.headers.map((header) => (
                <TableHead key={header.id}>
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {error ? (
            <TableRow>
              <TableCell
                colSpan={colCount}
                className="py-8 text-center text-destructive"
              >
                {error instanceof Error ? error.message : 'An error occurred.'}
              </TableCell>
            </TableRow>
          ) : isLoading ? (
            Array.from({ length: skeletonRows }).map((_r, i) => (
              <TableRow key={i}>
                {Array.from({ length: colCount }).map((_c, j) => (
                  <TableCell key={j}>
                    <Skeleton className="h-4 w-full" />
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : rows.length === 0 ? (
            <TableRow>
              <TableCell
                colSpan={colCount}
                className="py-8 text-center text-muted-foreground"
              >
                {emptyMessage}
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row) => (
              <TableRow
                key={row.id}
                onClick={
                  onRowClick ? () => onRowClick(row.original) : undefined
                }
                className={onRowClick ? 'cursor-pointer' : undefined}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {hasData && (
        <div className="flex items-center justify-end gap-2 px-2 text-xs text-muted-foreground">
          <span>
            Page {pagination.pageIndex + 1} of {pageCount}
          </span>
          <Button
            variant="outline"
            size="icon-sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            aria-label="Previous page"
          >
            <CaretLeftIcon />
          </Button>
          <Button
            variant="outline"
            size="icon-sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            aria-label="Next page"
          >
            <CaretRightIcon />
          </Button>
        </div>
      )}
    </div>
  )
}
