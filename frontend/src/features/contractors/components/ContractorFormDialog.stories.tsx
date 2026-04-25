import type { Meta, StoryObj } from "@storybook/react-vite";
import type { Contractor } from "@/api/generated/types.gen";
import { ContractorFormDialog } from "./ContractorFormDialog";

const SAMPLE_CONTRACTOR: Contractor = {
  id: 5,
  name: "Acme Corp",
  address: "123 Main St",
  city: "Brooklyn",
  state: "NY",
  zip_code: "11201",
};

const meta: Meta<typeof ContractorFormDialog> = {
  title: "Features/Contractors/ContractorFormDialog",
  component: ContractorFormDialog,
  args: {
    open: true,
    onOpenChange: () => {},
  },
};

export default meta;
type Story = StoryObj<typeof ContractorFormDialog>;

export const Create: Story = {};

export const Edit: Story = {
  args: {
    contractor: SAMPLE_CONTRACTOR,
  },
};
