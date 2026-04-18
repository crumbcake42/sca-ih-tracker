import type { UseFormSetError, FieldValues, Path } from 'react-hook-form'

type FastApiDetail = Array<{
  loc: (string | number)[]
  msg: string
  type: string
}>

function isFastApi422(err: unknown): err is { detail: FastApiDetail } {
  return (
    typeof err === 'object' &&
    err !== null &&
    'detail' in err &&
    Array.isArray((err as { detail: unknown }).detail)
  )
}

export function applyServerErrors<T extends FieldValues>(
  err: unknown,
  setError: UseFormSetError<T>,
): boolean {
  if (!isFastApi422(err)) return false

  for (const item of err.detail) {
    const field = item.loc.at(-1)
    if (typeof field === 'string') {
      setError(field as Path<T>, { message: item.msg })
    }
  }
  return true
}
