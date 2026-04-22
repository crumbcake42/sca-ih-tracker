import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckIcon, CaretUpDownIcon } from "@phosphor-icons/react";
import { listSchoolsOptions } from "@/features/schools/api/schools";
import { useDebounce } from "@/hooks/useDebounce";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

type Props = {
  value: number | null;
  onChange: (id: number | null) => void;
  disabled?: boolean;
};

export function SchoolCombobox({ value, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 250);

  const { data } = useQuery(
    listSchoolsOptions({
      query: { search: debouncedSearch || null },
    }),
  );
  const schools = data?.items ?? [];

  const selected = schools.find((s) => s.id === value) ?? null;

  function handleSelect(id: number) {
    onChange(id === value ? null : id);
    setOpen(false);
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
          {selected ? `${selected.code} — ${selected.name}` : "Select school…"}
          <CaretUpDownIcon className="ml-2 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search schools…"
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            <CommandEmpty>No schools found.</CommandEmpty>
            <CommandGroup>
              {schools.map((school) => (
                <CommandItem
                  key={school.id}
                  value={String(school.id)}
                  onSelect={() => handleSelect(school.id)}
                  data-checked={school.id === value}
                >
                  <CheckIcon
                    className={cn(
                      "mr-2",
                      school.id === value ? "opacity-100" : "opacity-0",
                    )}
                  />
                  {school.code} — {school.name}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
