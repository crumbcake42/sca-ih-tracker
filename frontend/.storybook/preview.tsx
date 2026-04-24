import type { Preview, Decorator } from "@storybook/react-vite";
import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "../src/test/queryClient";

import "../src/styles.css";

const withQueryClient: Decorator = (Story) => {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <Story />
    </QueryClientProvider>
  );
};

/** Applies .dark class to the story root so shadcn tokens respond to the theme toolbar. */
const withTheme: Decorator = (Story, context) => {
  const theme = (context.globals["theme"] as string | undefined) ?? "light";
  return (
    <div className={theme === "dark" ? "dark" : ""}>
      <Story />
    </div>
  );
};

const preview: Preview = {
  globalTypes: {
    theme: {
      description: "Color theme",
      defaultValue: "light",
      toolbar: {
        title: "Theme",
        icon: "circlehollow",
        items: [
          { value: "light", title: "Light", icon: "sun" },
          { value: "dark", title: "Dark", icon: "moon" },
        ],
        dynamicTitle: true,
      },
    },
  },
  decorators: [withTheme, withQueryClient],
  parameters: {
    layout: "padded",
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    a11y: {
      test: "todo",
    },
  },
};

export default preview;
