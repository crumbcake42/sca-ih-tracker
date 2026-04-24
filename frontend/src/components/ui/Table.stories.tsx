import type { Meta, StoryObj } from "@storybook/react-vite";
import { Badge } from "./badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./table";

const meta: Meta = {
  title: "UI/Table",
};

export default meta;
type Story = StoryObj;

const rows = [
  { id: 1, name: "Jane Smith", role: "Hygienist", status: "active" },
  { id: 2, name: "Bob Jones", role: "Technician", status: "active" },
  { id: 3, name: "Alice Wu", role: "Supervisor", status: "inactive" },
];

export const Default: Story = {
  render: () => (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Role</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.id}>
            <TableCell>{row.name}</TableCell>
            <TableCell>{row.role}</TableCell>
            <TableCell>
              <Badge variant={row.status === "active" ? "default" : "outline"}>
                {row.status}
              </Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  ),
};

export const Empty: Story = {
  render: () => (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Role</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow>
          <TableCell colSpan={2} className="text-center text-muted-foreground">
            No records found.
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  ),
};
