import type { Config } from './generated/client'

// Called by the generated client bundle to get initial configuration.
// Auth header injection is wired in Session 0.2 once the Zustand store exists.

// SSR-safe token getter — replaced in Session 0.2 with the Zustand store reader.
let _getToken: () => string | null = () => null

export function setTokenGetter(getter: () => string | null) {
  _getToken = getter
}

export function getToken() {
  return _getToken()
}

export function createClientConfig(override?: Partial<Config>) {
  return {
    baseUrl:
      typeof import.meta !== 'undefined'
        ? (import.meta.env?.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000')
        : 'http://127.0.0.1:8000',
    ...override,
  }
}
