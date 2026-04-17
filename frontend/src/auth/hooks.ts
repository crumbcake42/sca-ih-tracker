import { useMutation } from '@tanstack/react-query'
import {
  getMeUsersMeGet,
  loginForAccessTokenAuthTokenPost,
} from '../api/generated/sdk.gen'
import { useAuthStore } from './store'
import type { AuthUser } from './store'

export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth)

  return useMutation({
    mutationFn: async ({
      username,
      password,
    }: {
      username: string
      password: string
    }) => {
      const { data: tokenData, error: tokenError } =
        await loginForAccessTokenAuthTokenPost({
          body: { username, password },
        })
      if (tokenError || !tokenData)
        throw tokenError ?? new Error('Login failed')

      const token = (tokenData as { access_token: string }).access_token

      const { data: userData, error: meError } = await getMeUsersMeGet({
        headers: { Authorization: `Bearer ${token}` },
      })
      if (meError || !userData)
        throw meError ?? new Error('Failed to fetch user')

      setAuth(token, userData as AuthUser)
      return userData as AuthUser
    },
  })
}

export function useLogout() {
  return useAuthStore((s) => s.clearAuth)
}

export function useCurrentUser() {
  return useAuthStore((s) => s.user)
}

export function useIsAuthenticated() {
  return useAuthStore((s) => !!s.token)
}
