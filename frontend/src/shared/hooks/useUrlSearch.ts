import { useNavigate, useSearch } from '@tanstack/react-router'

/**
 * Syncs a single string filter with a URL search param.
 * Setting the value also resets `page` to 1 so results start from the beginning.
 *
 * @param param - The URL search param key (default: "search")
 */
export function useUrlSearch(param = 'search') {
  const navigate = useNavigate()
  const search = useSearch({ strict: false }) as Record<string, unknown>

  const value = String(search[param] ?? '')

  const setValue = (v: string) => {
    void navigate({
      search: (prev) => ({
        ...(prev as Record<string, unknown>),
        [param]: v || undefined,
        page: undefined,
      }),
    })
  }

  return [value, setValue] as const
}
