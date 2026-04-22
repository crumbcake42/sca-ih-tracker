import { QueryClient } from "@tanstack/react-query";

/** Creates a test-scoped QueryClient with retries and caching disabled. */
export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}
