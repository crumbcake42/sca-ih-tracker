import type { Meta, StoryObj } from "@storybook/react-vite";
import { Button } from "./button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "./command";
import {
  Popover,
  PopoverContent,
  PopoverDescription,
  PopoverHeader,
  PopoverTitle,
  PopoverTrigger,
} from "./popover";

const meta: Meta = {
  title: "UI/Overlay",
};

export default meta;
type Story = StoryObj;

export const PopoverStory: Story = {
  name: "Popover",
  render: () => (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline">Open popover</Button>
      </PopoverTrigger>
      <PopoverContent>
        <PopoverHeader>
          <PopoverTitle>Filter options</PopoverTitle>
          <PopoverDescription>
            Adjust the filters applied to this list.
          </PopoverDescription>
        </PopoverHeader>
        <p className="text-xs text-muted-foreground">
          Additional controls go here.
        </p>
      </PopoverContent>
    </Popover>
  ),
};

const fruits = ["Apple", "Banana", "Cherry", "Date", "Elderberry", "Fig"];

export const CommandStory: Story = {
  name: "Command",
  render: () => (
    <div className="w-72 rounded-none ring-1 ring-foreground/10">
      <Command>
        <CommandInput placeholder="Search…" />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Fruits">
            {fruits.map((fruit) => (
              <CommandItem key={fruit} value={fruit}>
                {fruit}
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </Command>
    </div>
  ),
};
