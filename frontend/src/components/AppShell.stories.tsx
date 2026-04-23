import type { Meta, StoryObj, Decorator } from "@storybook/react-vite";
import {
  createRouter,
  createRootRoute,
  RouterProvider,
  createMemoryHistory,
} from "@tanstack/react-router";
import type { User } from "@/api/generated/types.gen";
import { useAuthStore } from "@/auth/store";
import { AppShell } from "./AppShell";

const fakeUser: User = {
  id: 2,
  first_name: "Jane",
  last_name: "Manager",
  username: "jane.manager",
  email: "jane@example.com",
  date_created: "2025-01-01T00:00:00Z",
  role: { name: "admin", permissions: [] },
};

/** Provides a minimal in-memory router so <Link> components render without crashing. */
const withRouter: Decorator = (Story) => {
  const rootRoute = createRootRoute({ component: Story });
  const router = createRouter({
    routeTree: rootRoute,
    history: createMemoryHistory(),
  });
  return <RouterProvider router={router} />;
};

const meta: Meta<typeof AppShell> = {
  title: "Shared/AppShell",
  component: AppShell,
  decorators: [withRouter],
  parameters: { layout: "fullscreen" },
};

export default meta;
type Story = StoryObj<typeof AppShell>;

export const Default: Story = {
  decorators: [
    (Story) => {
      useAuthStore.setState({ user: fakeUser, token: "fake-token" });
      return <Story />;
    },
  ],
  args: {
    children: (
      <div className="p-4 text-muted-foreground">Page content goes here.</div>
    ),
  },
};

export const Unauthenticated: Story = {
  decorators: [
    (Story) => {
      useAuthStore.setState({ user: null, token: null });
      return <Story />;
    },
  ],
  args: {
    children: (
      <div className="p-4 text-muted-foreground">Page content goes here.</div>
    ),
  },
};
