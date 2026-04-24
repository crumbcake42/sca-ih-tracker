import type { Meta, StoryObj, Decorator } from "@storybook/react-vite";
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getWaCodeConnectionsQueryKey } from "@/features/wa-codes/api/wa-codes";
import { WaCodeFormDialog } from "./WaCodeFormDialog";
import type { WaCode } from "@/api/generated/types.gen";

const SAMPLE_WA_CODE: WaCode = {
  id: 10,
  code: "MOLD-01",
  description: "Bulk mold sampling — project-wide",
  level: "project",
  default_fee: "150.00",
};

const connectionKey = getWaCodeConnectionsQueryKey({
  path: { wa_code_id: SAMPLE_WA_CODE.id },
});

/** Seeds the connections cache with an empty object — level remains enabled. */
const withNoConnections: Decorator = (Story) => {
  const queryClient = useQueryClient();
  useEffect(() => {
    queryClient.setQueryData(connectionKey, {});
  }, [queryClient]);
  return <Story />;
};

/** Seeds the connections cache with active links — level becomes disabled. */
const withConnections: Decorator = (Story) => {
  const queryClient = useQueryClient();
  useEffect(() => {
    queryClient.setQueryData(connectionKey, { work_auths: 3, sample_types: 1 });
  }, [queryClient]);
  return <Story />;
};

const meta: Meta<typeof WaCodeFormDialog> = {
  title: "Features/WaCodes/WaCodeFormDialog",
  component: WaCodeFormDialog,
  args: {
    open: true,
    onOpenChange: () => {},
  },
};

export default meta;
type Story = StoryObj<typeof WaCodeFormDialog>;

export const Create: Story = {};

export const EditNoConnections: Story = {
  args: { waCode: SAMPLE_WA_CODE },
  decorators: [withNoConnections],
};

export const EditLevelLocked: Story = {
  args: { waCode: SAMPLE_WA_CODE },
  decorators: [withConnections],
};
