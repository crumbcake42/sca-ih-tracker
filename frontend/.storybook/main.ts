import type { StorybookConfig } from "@storybook/react-vite";

const storybookConfig: StorybookConfig = {
  stories: ["../src/**/*.mdx", "../src/**/*.stories.@(js|jsx|mjs|ts|tsx)"],
  addons: [
    "@chromatic-com/storybook",
    "@storybook/addon-vitest",
    "@storybook/addon-a11y",
    "@storybook/addon-docs",
  ],
  framework: "@storybook/react-vite",
  viteFinal: async (config) => {
    // Strip TanStack Start/Router SSR plugins — same reason vitest has its own config.
    config.plugins = (config.plugins ?? []).filter((p) => {
      if (!p || Array.isArray(p)) return true;
      const name = (p as { name?: string }).name ?? "";
      return !name.includes("tanstack");
    });
    return config;
  },
};

export default storybookConfig;
