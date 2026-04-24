import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "@/test/queryClient";
import { EntityListPage } from "./EntityListPage";
import type { ColumnDef } from "@tanstack/react-table";
import type { QueryKey, QueryFunction } from "@tanstack/react-query";
import type { Paginated } from "./EntityListPage";
import type { ReactNode } from "react";

// --- Router mocks (useUrlSearch/useUrlPagination depend on TanStack Router) ---

const mockNavigate = vi.fn();
let mockSearch: Record<string, unknown> = {};

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => mockNavigate,
  useSearch: () => mockSearch,
}));

// --- Fixture ---

type Item = { id: number; name: string };

const FIXTURE: Paginated<Item> = {
  items: [
    { id: 1, name: "Alpha" },
    { id: 2, name: "Beta" },
  ],
  total: 2,
  skip: 0,
  limit: 20,
};

const columns: ColumnDef<Item>[] = [
  { accessorKey: "id", header: "ID" },
  { accessorKey: "name", header: "Name" },
];

type ItemQueryFactory = (options?: unknown) => {
  queryKey: QueryKey;
  queryFn: QueryFunction<Paginated<Item>, never, never>;
};

function makeQueryOptions(data: Paginated<Item> = FIXTURE): ItemQueryFactory {
  return () => ({
    queryKey: ["items"],
    queryFn: async () => data,
  });
}

type PageProps = {
  title?: string;
  columns?: ColumnDef<Item>[];
  queryOptions?: ItemQueryFactory;
  searchPlaceholder?: string;
  emptyMessage?: string;
  actions?: ReactNode;
  onRowClick?: (row: Item) => void;
};

function renderPage(props?: PageProps) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <EntityListPage<Item>
        title="Items"
        columns={columns}
        queryOptions={makeQueryOptions()}
        searchPlaceholder="Search items…"
        emptyMessage="No items found."
        {...props}
      />
    </QueryClientProvider>,
  );
}

describe("EntityListPage", () => {
  beforeEach(() => {
    mockSearch = {};
    mockNavigate.mockClear();
  });

  it("renders the title and column headers", async () => {
    renderPage();
    expect(screen.getByRole("heading", { name: "Items" })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("ID")).toBeInTheDocument();
      expect(screen.getByText("Name")).toBeInTheDocument();
    });
  });

  it("renders rows from the paginated response", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Alpha")).toBeInTheDocument();
      expect(screen.getByText("Beta")).toBeInTheDocument();
    });
  });

  it("shows empty message when items array is empty", async () => {
    renderPage({
      queryOptions: makeQueryOptions({
        items: [],
        total: 0,
        skip: 0,
        limit: 20,
      }) as never,
    });
    await waitFor(() => {
      expect(screen.getByText("No items found.")).toBeInTheDocument();
    });
  });

  it("renders the actions slot", () => {
    renderPage({
      actions: <button>Custom Action</button>,
    });
    expect(
      screen.getByRole("button", { name: "Custom Action" }),
    ).toBeInTheDocument();
  });

  it("calls onRowClick when a data row is clicked", async () => {
    const onRowClick = vi.fn();
    renderPage({ onRowClick });

    await waitFor(() => {
      expect(screen.getByText("Alpha")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Alpha"));
    expect(onRowClick).toHaveBeenCalledWith(FIXTURE.items[0]);
  });

  it("calls navigate when search input changes", async () => {
    renderPage();
    const input = screen.getByPlaceholderText("Search items…");
    await userEvent.type(input, "x");
    expect(mockNavigate).toHaveBeenCalled();
  });
});
