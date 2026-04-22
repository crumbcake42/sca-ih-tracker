import type { Meta, StoryObj, Decorator } from "@storybook/react-vite";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import type { PaginatedResponseSchool } from "@/api/generated/types.gen";
import { listSchoolsQueryKey } from "@/features/schools/api/schools";
import { SchoolCombobox } from "./SchoolCombobox";

const fakeSchools: PaginatedResponseSchool = {
  items: [
    { id: 1, code: "Q001", name: "PS 1 Bergen", address: "1 Main St", city: "QUEENS", state: "NY", zip_code: "11101", created_at: "2025-01-01T00:00:00Z" },
    { id: 2, code: "Q002", name: "PS 2 Ridgewood", address: "2 Oak Ave", city: "QUEENS", state: "NY", zip_code: "11385", created_at: "2025-01-01T00:00:00Z" },
    { id: 3, code: "K003", name: "PS 3 Bedford", address: "3 Elm Rd", city: "BROOKLYN", state: "NY", zip_code: "11205", created_at: "2025-01-01T00:00:00Z" },
  ],
  total: 3,
  skip: 0,
  limit: 50,
};

/** Pre-seeds the QueryClient cache with fake school data so no network call is made. */
const withSchoolsSeeded: Decorator = (Story) => {
  const queryClient = useQueryClient();
  useEffect(() => {
    queryClient.setQueryData(
      listSchoolsQueryKey({ query: { search: null } }),
      fakeSchools,
    );
  }, [queryClient]);
  return <Story />;
};

function Controlled({ initialValue = null }: { initialValue?: number | null }) {
  const [value, setValue] = useState<number | null>(initialValue);
  return <SchoolCombobox value={value} onChange={setValue} />;
}

const meta: Meta<typeof Controlled> = {
  title: "Fields/SchoolCombobox",
  component: Controlled,
  decorators: [withSchoolsSeeded],
};

export default meta;
type Story = StoryObj<typeof Controlled>;

export const Default: Story = {};

export const WithSelection: Story = {
  args: { initialValue: 2 },
};
