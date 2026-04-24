import type { Meta, StoryObj, Decorator } from "@storybook/react-vite";
import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

import type { Employee } from "@/api/generated/types.gen";
import { listEmployeesQueryKey } from "@/features/employees/api/employees";
import { EmployeeCombobox } from "./EmployeeCombobox";

const fakeEmployees: Employee[] = [
  { id: 1, first_name: "Alice", last_name: "Hygienist" },
  { id: 2, first_name: "Bob", last_name: "Inspector" },
  { id: 3, first_name: "Carol", last_name: "Coordinator" },
];

/** Pre-seeds the QueryClient cache with a paginated envelope so no network call is made. */
const withEmployeesSeeded: Decorator = (Story) => {
  const queryClient = useQueryClient();
  useEffect(() => {
    queryClient.setQueryData(listEmployeesQueryKey(), {
      items: fakeEmployees,
      total: fakeEmployees.length,
      skip: 0,
      limit: 100,
    });
  }, [queryClient]);
  return <Story />;
};

function Controlled({ initialValue = null }: { initialValue?: number | null }) {
  const [value, setValue] = useState<number | null>(initialValue);
  return <EmployeeCombobox value={value} onChange={setValue} />;
}

const meta: Meta<typeof Controlled> = {
  title: "Fields/EmployeeCombobox",
  component: Controlled,
  decorators: [withEmployeesSeeded],
};

export default meta;
type Story = StoryObj<typeof Controlled>;

export const Default: Story = {};

export const WithSelection: Story = {
  args: { initialValue: 2 },
};
