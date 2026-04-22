import { useNavigate, useSearch } from "@tanstack/react-router";

/**
 * Syncs a single string filter with a URL search param.
 * Setting the value also resets `page` to 1 so results start from the beginning.
 *
 * @param param - The URL search param key (default: "search")
 */
export function useUrlSearch(param = "search") {
  const navigate = useNavigate();
  const search = useSearch({ strict: false });

  const value = String((search as Record<string, unknown>)[param] ?? "");

  const setValue = (v: string) => {
    void navigate({
      search: ((prev: Record<string, unknown>) => ({
        ...prev,
        [param]: v || undefined,
        page: undefined,
      })) as never,
    });
  };

  return [value, setValue] as const;
}
