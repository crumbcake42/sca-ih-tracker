import type { Meta, StoryObj } from "@storybook/react-vite";
import { PlusIcon } from "@phosphor-icons/react";
import { Button } from "./button";

const meta: Meta<typeof Button> = {
  title: "UI/Button",
  component: Button,
  args: { children: "Button" },
};

export default meta;
type Story = StoryObj<typeof Button>;

export const Default: Story = {};
export const Outline: Story = { args: { variant: "outline" } };
export const Secondary: Story = { args: { variant: "secondary" } };
export const Ghost: Story = { args: { variant: "ghost" } };
export const Destructive: Story = { args: { variant: "destructive" } };
export const Link: Story = { args: { variant: "link" } };
export const Disabled: Story = { args: { disabled: true } };

export const AllVariants: Story = {
  name: "All variants",
  render: () => (
    <div className="flex flex-wrap items-center gap-2">
      <Button>Default</Button>
      <Button variant="outline">Outline</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="ghost">Ghost</Button>
      <Button variant="destructive">Destructive</Button>
      <Button variant="link">Link</Button>
    </div>
  ),
};

export const AllSizes: Story = {
  name: "All sizes",
  render: () => (
    <div className="flex flex-wrap items-center gap-2">
      <Button size="xs">XSmall</Button>
      <Button size="sm">Small</Button>
      <Button size="default">Default</Button>
      <Button size="lg">Large</Button>
      <Button size="icon">
        <PlusIcon />
      </Button>
      <Button size="icon-sm">
        <PlusIcon />
      </Button>
      <Button size="icon-xs">
        <PlusIcon />
      </Button>
    </div>
  ),
};

export const WithIcon: Story = {
  name: "With icon",
  render: () => (
    <div className="flex flex-wrap items-center gap-2">
      <Button>
        <PlusIcon data-icon="inline-start" />
        Add item
      </Button>
      <Button variant="outline">
        Add item
        <PlusIcon data-icon="inline-end" />
      </Button>
    </div>
  ),
};
