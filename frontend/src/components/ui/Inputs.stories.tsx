import type { Meta, StoryObj } from "@storybook/react-vite";
import { MagnifyingGlassIcon } from "@phosphor-icons/react";
import { Badge } from "./badge";
import { Checkbox } from "./checkbox";
import { Field, FieldError, FieldGroup, FieldLabel } from "./field";
import { Input } from "./input";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
  InputGroupText,
} from "./input-group";
import { Label } from "./label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./select";
import { Textarea } from "./textarea";

const meta: Meta = {
  title: "UI/Inputs",
};

export default meta;
type Story = StoryObj;

export const Inputs: Story = {
  render: () => (
    <div className="flex w-72 flex-col gap-4">
      <Field>
        <FieldLabel>Default</FieldLabel>
        <Input placeholder="Type something…" />
      </Field>
      <Field>
        <FieldLabel>Disabled</FieldLabel>
        <Input disabled placeholder="Can't touch this" />
      </Field>
      <Field data-invalid="true">
        <FieldLabel>Invalid</FieldLabel>
        <Input aria-invalid="true" placeholder="Bad value" />
        <FieldError>This field is required.</FieldError>
      </Field>
    </div>
  ),
};

export const TextareaStory: Story = {
  name: "Textarea",
  render: () => (
    <div className="flex w-72 flex-col gap-4">
      <Field>
        <FieldLabel>Notes</FieldLabel>
        <Textarea placeholder="Add a note…" rows={4} />
      </Field>
      <Field>
        <FieldLabel>Disabled</FieldLabel>
        <Textarea disabled placeholder="Read-only" />
      </Field>
    </div>
  ),
};

export const SelectStory: Story = {
  name: "Select",
  render: () => (
    <div className="flex w-72 flex-col gap-4">
      <Field>
        <FieldLabel>Role type</FieldLabel>
        <Select>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Pick a role…" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="hygienist">Hygienist</SelectItem>
            <SelectItem value="technician">Technician</SelectItem>
            <SelectItem value="supervisor">Supervisor</SelectItem>
          </SelectContent>
        </Select>
      </Field>
      <Field>
        <FieldLabel>Disabled</FieldLabel>
        <Select disabled>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Locked" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="x">x</SelectItem>
          </SelectContent>
        </Select>
      </Field>
    </div>
  ),
};

export const CheckboxStory: Story = {
  name: "Checkbox",
  render: () => (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Checkbox id="unchecked" />
        <Label htmlFor="unchecked">Unchecked</Label>
      </div>
      <div className="flex items-center gap-2">
        <Checkbox id="checked" defaultChecked />
        <Label htmlFor="checked">Checked</Label>
      </div>
      <div className="flex items-center gap-2">
        <Checkbox id="disabled" disabled />
        <Label htmlFor="disabled">Disabled</Label>
      </div>
    </div>
  ),
};

export const FieldGroupStory: Story = {
  name: "FieldGroup",
  render: () => (
    <FieldGroup className="w-72">
      <Field>
        <FieldLabel>First name</FieldLabel>
        <Input placeholder="Jane" />
      </Field>
      <Field>
        <FieldLabel>Last name</FieldLabel>
        <Input placeholder="Smith" />
      </Field>
      <Field data-invalid="true">
        <FieldLabel>Email</FieldLabel>
        <Input aria-invalid="true" placeholder="jane@example.com" />
        <FieldError>Must be a valid email address.</FieldError>
      </Field>
    </FieldGroup>
  ),
};

export const InputGroupStory: Story = {
  name: "InputGroup",
  render: () => (
    <div className="flex w-72 flex-col gap-4">
      <InputGroup>
        <InputGroupAddon align="inline-end">
          <MagnifyingGlassIcon />
        </InputGroupAddon>
        <InputGroupInput placeholder="Search…" />
      </InputGroup>
      <InputGroup>
        <InputGroupAddon align="inline-start">
          <InputGroupText>$</InputGroupText>
        </InputGroupAddon>
        <InputGroupInput placeholder="0.00" type="number" />
        <InputGroupAddon align="inline-end">
          <InputGroupText>USD</InputGroupText>
        </InputGroupAddon>
      </InputGroup>
      <InputGroup>
        <InputGroupInput placeholder="Search tags…" />
        <InputGroupAddon align="inline-end">
          <InputGroupButton>
            <Badge variant="secondary">3</Badge>
          </InputGroupButton>
        </InputGroupAddon>
      </InputGroup>
    </div>
  ),
};
