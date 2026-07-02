import { useCallback, useState } from 'react'

export function useRowSelection(rowIds: string[]) {
  const [selected, setSelected] = useState<Set<string>>(() => new Set())

  const allSelected = rowIds.length > 0 && rowIds.every((id) => selected.has(id))
  const someSelected = rowIds.some((id) => selected.has(id))
  const indeterminate = someSelected && !allSelected

  const toggleRow = useCallback((id: string, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (checked) next.add(id)
      else next.delete(id)
      return next
    })
  }, [])

  const toggleAll = useCallback(
    (checked: boolean) => {
      setSelected(checked ? new Set(rowIds) : new Set())
    },
    [rowIds],
  )

  return { selected, allSelected, indeterminate, toggleRow, toggleAll }
}
