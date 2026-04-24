import type { Meta, StoryObj } from "@storybook/react-vite";
import { Badge } from "./badge";
import { Separator } from "./separator";
import { Skeleton } from "./skeleton";

const meta: Meta = {
  title: "UI/Misc",
};

export default meta;
type Story = StoryObj;

export const Badges: Story = {
  render: () => (
    <div className="flex flex-wrap items-center gap-2">
      <Badge>Default</Badge>
      <Badge variant="secondary">Secondary</Badge>
      <Badge variant="outline">Outline</Badge>
      <Badge variant="destructive">Destructive</Badge>
      <Badge variant="ghost">Ghost</Badge>
    </div>
  ),
};

export const Separators: Story = {
  render: () => (
    <div className="flex w-64 flex-col gap-4">
      <span>Above</span>
      <Separator />
      <span>Below</span>
      <Separator orientation="horizontal" />
      <div className="flex h-8 items-center gap-4">
        <span>Left</span>
        <Separator orientation="vertical" />
        <span>Right</span>
      </div>
    </div>
  ),
};

export const Skeletons: Story = {
  render: () => (
    <div className="flex w-64 flex-col gap-3">
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <div className="flex items-center gap-3 pt-2">
        <Skeleton className="size-8 rounded-full" />
        <div className="flex flex-1 flex-col gap-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      </div>
    </div>
  ),
};
