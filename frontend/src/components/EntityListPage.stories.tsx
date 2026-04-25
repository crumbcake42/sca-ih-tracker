import type { Meta, StoryObj, Decorator } from "@storybook/react-vite";
import type { ColumnDef } from "@tanstack/react-table";
import type { UseQueryOptions } from "@tanstack/react-query";
import {
  createRouter,
  createRootRoute,
  RouterProvider,
  createMemoryHistory,
} from "@tanstack/react-router";
import { PlusIcon } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { EntityListPage } from "./EntityListPage";
import type { Paginated } from "./EntityListPage";

type Row = { id: number; code: string; name: string };

const columns: ColumnDef<Row>[] = [
  {
    accessorKey: "code",
    header: "Code",
    cell: ({ getValue }) => (
      <span className="font-mono text-xs">{getValue<string>()}</span>
    ),
  },
  { accessorKey: "name", header: "Name" },
];

const FIXTURE: Paginated<Row> = {
  items: [
    { id: 1, code: "Q001", name: "PS 1 Manhattan" },
    { id: 2, code: "Q002", name: "PS 2 Brooklyn" },
    { id: 3, code: "Q003", name: "PS 3 Queens" },
  ],
  total: 3,
  skip: 0,
  limit: 20,
};

function makeQueryOptions(
  queryFn: () => Promise<Paginated<Row>>,
): () => UseQueryOptions<Paginated<Row>> {
  return () => ({ queryKey: ["story-rows"], queryFn });
}

/** Wraps the story in a minimal in-memory router so useSearch/useNavigate resolve. */
const withRouter: Decorator = (Story) => {
  const rootRoute = createRootRoute({ component: Story });
  const router = createRouter({
    routeTree: rootRoute,
    history: createMemoryHistory({ initialEntries: ["/admin/schools"] }),
  });
  return <RouterProvider router={router} />;
};

const meta: Meta<typeof EntityListPage<Row>> = {
  title: "Shared/EntityListPage",
  component: EntityListPage<Row>,
  decorators: [withRouter],
  parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof EntityListPage<Row>>;

export const Default: Story = {
  args: {
    title: "Schools",
    columns,
    queryOptions: makeQueryOptions(async () => FIXTURE) as never,
    searchPlaceholder: "Search schools…",
    emptyMessage: "No schools found.",
  },
};

export const WithActions: Story = {
  args: {
    ...Default.args,
    actions: (
      <Button size="sm">
        <PlusIcon size={15} />
        Import CSV
      </Button>
    ),
  },
};

export const Loading: Story = {
  args: {
    ...Default.args,
    // queryFn that never resolves keeps the skeleton visible
    queryOptions: makeQueryOptions(() => new Promise(() => {})) as never,
  },
};

export const Empty: Story = {
  args: {
    ...Default.args,
    queryOptions: makeQueryOptions(async () => ({
      items: [],
      total: 0,
      skip: 0,
      limit: 20,
    })) as never,
  },
};

export const TableError: Story = {
  name: "Error",
  args: {
    ...Default.args,
    queryOptions: makeQueryOptions(async () => {
      throw new Error("Failed to load.");
    }) as never,
  },
};
