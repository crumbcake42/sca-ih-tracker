import type { Meta, StoryObj } from "@storybook/react-vite";
import type { ColumnDef, PaginationState } from "@tanstack/react-table";
import { useState } from "react";
import { DataTable } from "./DataTable";

type Row = { id: number; name: string; code: string };

const columns: ColumnDef<Row>[] = [
  { accessorKey: "code", header: "Code" },
  { accessorKey: "name", header: "Name" },
];

const rows: Row[] = [
  { id: 1, code: "Q001", name: "PS 1" },
  { id: 2, code: "Q002", name: "PS 2" },
  { id: 3, code: "Q003", name: "PS 3" },
];

function Wrapper(
  props: Omit<
    Parameters<typeof DataTable<Row>>[0],
    "pagination" | "onPaginationChange"
  >,
) {
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  });
  return (
    <DataTable
      {...props}
      pagination={pagination}
      onPaginationChange={setPagination}
    />
  );
}

const meta: Meta<typeof Wrapper> = {
  title: "Shared/DataTable",
  component: Wrapper,
};

export default meta;
type Story = StoryObj<typeof Wrapper>;

export const Default: Story = {
  args: { columns, data: rows, pageCount: 1 },
};

export const Loading: Story = {
  args: { columns, data: [], pageCount: 0, isLoading: true },
};

export const Empty: Story = {
  args: { columns, data: [], pageCount: 0, emptyMessage: "No schools found." },
};

export const TableError: Story = {
  name: "Error",
  args: {
    columns,
    data: [],
    pageCount: 0,
    error: new Error("Failed to load data."),
  },
};
