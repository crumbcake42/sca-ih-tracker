import type { Meta, StoryObj } from "@storybook/react-vite";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./tabs";

const meta: Meta = {
  title: "UI/Tabs",
};

export default meta;
type Story = StoryObj;

export const Default: Story = {
  render: () => (
    <Tabs defaultValue="details" className="w-80">
      <TabsList>
        <TabsTrigger value="details">Details</TabsTrigger>
        <TabsTrigger value="roles">Roles</TabsTrigger>
        <TabsTrigger value="notes">Notes</TabsTrigger>
        <TabsTrigger value="disabled" disabled>
          Disabled
        </TabsTrigger>
      </TabsList>
      <TabsContent value="details" className="p-2">
        Details content
      </TabsContent>
      <TabsContent value="roles" className="p-2">
        Roles content
      </TabsContent>
      <TabsContent value="notes" className="p-2">
        Notes content
      </TabsContent>
    </Tabs>
  ),
};

export const LineVariant: Story = {
  name: "Line variant",
  render: () => (
    <Tabs defaultValue="active" className="w-80">
      <TabsList variant="line">
        <TabsTrigger value="active">Active</TabsTrigger>
        <TabsTrigger value="archived">Archived</TabsTrigger>
        <TabsTrigger value="all">All</TabsTrigger>
      </TabsList>
      <TabsContent value="active" className="p-2">
        Active items
      </TabsContent>
      <TabsContent value="archived" className="p-2">
        Archived items
      </TabsContent>
      <TabsContent value="all" className="p-2">
        All items
      </TabsContent>
    </Tabs>
  ),
};
