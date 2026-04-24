import type { Meta, StoryObj } from "@storybook/react-vite";
import { Button } from "./button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "./card";

const meta: Meta = {
  title: "UI/Card",
};

export default meta;
type Story = StoryObj;

export const Default: Story = {
  render: () => (
    <Card className="w-80">
      <CardHeader>
        <CardTitle>Card title</CardTitle>
        <CardDescription>A short description of the card.</CardDescription>
      </CardHeader>
      <CardContent>Card body content goes here.</CardContent>
      <CardFooter>
        <Button variant="outline" size="sm">
          Cancel
        </Button>
        <Button size="sm">Confirm</Button>
      </CardFooter>
    </Card>
  ),
};

export const WithAction: Story = {
  name: "With action",
  render: () => (
    <Card className="w-80">
      <CardHeader>
        <CardTitle>Schools</CardTitle>
        <CardDescription>Manage registered schools.</CardDescription>
        <CardAction>
          <Button size="sm">Manage</Button>
        </CardAction>
      </CardHeader>
      <CardContent>42 schools active.</CardContent>
    </Card>
  ),
};

export const SmallSize: Story = {
  name: "Small size",
  render: () => (
    <Card className="w-64" size="sm">
      <CardHeader>
        <CardTitle>Compact card</CardTitle>
      </CardHeader>
      <CardContent>Less padding, tighter spacing.</CardContent>
    </Card>
  ),
};
