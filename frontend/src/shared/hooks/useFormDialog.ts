import { useState } from 'react'

/** Manages open/close state for a dialog that contains a form. Pass `onClose` to reset form state when the dialog closes. */
export function useFormDialog(onClose?: () => void) {
  const [open, setOpen] = useState(false)

  const onOpenChange = (next: boolean) => {
    setOpen(next)
    if (!next) onClose?.()
  }

  return { open, setOpen, onOpenChange }
}
