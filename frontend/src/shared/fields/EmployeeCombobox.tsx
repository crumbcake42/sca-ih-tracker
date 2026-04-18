import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckIcon, CaretUpDownIcon } from '@phosphor-icons/react'
import { listEmployeesEmployeesGetOptions } from '@/api/generated/@tanstack/react-query.gen'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'

type Props = {
  value: number | null
  onChange: (id: number | null) => void
  disabled?: boolean
}

export function EmployeeCombobox({ value, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')

  const { data: employees = [] } = useQuery(listEmployeesEmployeesGetOptions())

  const filtered = search
    ? employees.filter((e) =>
        `${e.first_name} ${e.last_name}`
          .toLowerCase()
          .includes(search.toLowerCase()),
      )
    : employees

  const selected = employees.find((e) => e.id === value) ?? null

  function handleSelect(id: number) {
    onChange(id === value ? null : id)
    setOpen(false)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className="w-full justify-between font-normal"
        >
          {selected
            ? `${selected.first_name} ${selected.last_name}`
            : 'Select employee…'}
          <CaretUpDownIcon className="ml-2 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search employees…"
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            <CommandEmpty>No employees found.</CommandEmpty>
            <CommandGroup>
              {filtered.map((employee) => (
                <CommandItem
                  key={employee.id}
                  value={String(employee.id)}
                  onSelect={() => handleSelect(employee.id)}
                  data-checked={employee.id === value}
                >
                  <CheckIcon
                    className={cn(
                      'mr-2',
                      employee.id === value ? 'opacity-100' : 'opacity-0',
                    )}
                  />
                  {employee.first_name} {employee.last_name}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
