// Cross-cutting auth helpers — exempt from the feature api/ wrapper rule.
// Used by _authenticated.tsx route guard to validate tokens against /users/me.
export {
  getMeUsersMeGetOptions as currentUserOptions,
  getMeUsersMeGetQueryKey as currentUserQueryKey,
} from "@/api/generated/@tanstack/react-query.gen";
