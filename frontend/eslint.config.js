// For more info, see https://github.com/storybookjs/eslint-plugin-storybook#configuration-flat-config-format
import storybook from "eslint-plugin-storybook";
import eslintPluginPrettier from "eslint-plugin-prettier/recommended";

//  @ts-check

import { tanstackConfig } from "@tanstack/eslint-config";

export default [
  ...tanstackConfig,
  {
    rules: {
      "import/no-cycle": "off",
      "import/order": "off",
      "sort-imports": "off",
      "@typescript-eslint/array-type": "off",
      "@typescript-eslint/require-await": "off",
      "pnpm/json-enforce-catalog": "off",
      "@typescript-eslint/no-unnecessary-condition": "off",
    },
  }, // Feature components/hooks must not bypass the api/ wrapper layer or import from routing layers.
  // Feature api/ wrappers are exempt — they ARE the bridge to @/api/generated/.
  {
    files: ["src/features/*/components/**", "src/features/*/hooks/**"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["**/pages/**", "**/routes/**"],
              message:
                "Features are routing-agnostic — do not import from pages/ or routes/.",
            },
            {
              // types.gen is allowed everywhere (types policy). Only sdk.gen and query helpers are restricted.
              group: [
                "**/api/generated/sdk.gen*",
                "**/api/generated/@tanstack/**",
              ],
              message:
                "Import from @/features/<domain>/api/ instead of @/api/generated/ directly.",
            },
          ],
        },
      ],
    },
  }, // Pages must not bypass the feature api/ wrapper layer.
  {
    files: ["src/pages/**"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              // types.gen is allowed everywhere (types policy). Only sdk.gen and query helpers are restricted.
              group: [
                "**/api/generated/sdk.gen*",
                "**/api/generated/@tanstack/**",
              ],
              message:
                "Import from @/features/<domain>/api/ instead of @/api/generated/ directly.",
            },
          ],
        },
      ],
    },
  }, // Routes are config-only — they import from @/pages/ and @/auth/ only.
  {
    files: ["src/routes/**"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["**/features/**"],
              message:
                "Route files import only from @/pages/. Move logic to a page component.",
            },
            {
              group: ["**/api/generated/**"],
              message:
                "Route files import only from @/pages/. Use the feature api/ wrapper instead.",
            },
          ],
        },
      ],
    },
  },
  {
    ignores: [
      "eslint.config.js",
      "prettier.config.js",
      "src/api/generated/**",
      "src/routeTree.gen.ts",
    ],
  },
  ...storybook.configs["flat/recommended"],
  eslintPluginPrettier,
];
