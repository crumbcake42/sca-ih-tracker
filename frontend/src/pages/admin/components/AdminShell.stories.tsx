import type { Meta, StoryObj, Decorator } from "@storybook/react-vite";
import {
  createRouter,
  createRootRoute,
  RouterProvider,
  createMemoryHistory,
} from "@tanstack/react-router";
import type { User } from "@/api/generated/types.gen";
import { useAuthStore } from "@/auth/store";
import { useAdminShellStore } from "@/lib/admin-shell-state";
import { AdminShell } from "./AdminShell";

const fakeAdminUser: User = {
  id: 2,
  first_name: "Jane",
  last_name: "Admin",
  username: "jane.admin",
  email: "jane@example.com",
  date_created: "2025-01-01T00:00:00Z",
  role: { name: "admin", permissions: [] },
};

/** Provides an in-memory router at /admin so useRouterState resolves correctly. */
const withRouter: Decorator = (Story) => {
  const rootRoute = createRootRoute({ component: Story });
  const router = createRouter({
    routeTree: rootRoute,
    history: createMemoryHistory({ initialEntries: ["/admin"] }),
  });
  return <RouterProvider router={router} />;
};

const meta: Meta<typeof AdminShell> = {
  title: "Admin/AdminShell",
  component: AdminShell,
  decorators: [withRouter],
  parameters: { layout: "fullscreen" },
};

export default meta;
type Story = StoryObj<typeof AdminShell>;

const sampleContent = (
  <div className="space-y-4">
    <p className="text-sm text-muted-foreground">
      Sample page content rendered inside the admin shell.
    </p>
    <div className="rounded-md border p-4">
      <p className="text-sm font-medium">Content area</p>
      <p className="mt-1 text-xs text-muted-foreground">
        Scrollable, padded, and independent of the sidebar.
      </p>
    </div>
  </div>
);

export const Default: Story = {
  decorators: [
    (Story) => {
      useAuthStore.setState({ user: fakeAdminUser, token: "fake-token" });
      useAdminShellStore.setState({
        sidebarCollapsed: false,
        pageTitle: "Dashboard",
        pageActions: null,
      });
      return <Story />;
    },
  ],
  args: { children: sampleContent },
};

export const Collapsed: Story = {
  decorators: [
    (Story) => {
      useAuthStore.setState({ user: fakeAdminUser, token: "fake-token" });
      useAdminShellStore.setState({
        sidebarCollapsed: true,
        pageTitle: "Schools",
        pageActions: null,
      });
      return <Story />;
    },
  ],
  args: { children: sampleContent },
};

export const WithSamplePage: Story = {
  decorators: [
    (Story) => {
      useAuthStore.setState({ user: fakeAdminUser, token: "fake-token" });
      useAdminShellStore.setState({
        sidebarCollapsed: false,
        pageTitle: "Employees",
        pageActions: null,
      });
      return <Story />;
    },
  ],
  args: {
    children: (
      <div className="space-y-4">
        <div className="rounded-md border">
          <div className="border-b px-4 py-3">
            <p className="text-sm font-medium">Employee list</p>
          </div>
          {["Alice Chen", "Bob Torres", "Carol Smith"].map((name) => (
            <div key={name} className="border-b px-4 py-3 last:border-0">
              <p className="text-sm">{name}</p>
            </div>
          ))}
        </div>
      </div>
    ),
  },
};
