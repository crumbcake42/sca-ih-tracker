import type { Meta, StoryObj } from "@storybook/react-vite";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";

const meta: Meta = {
  title: "UI/Showcase",
  parameters: { layout: "fullscreen" },
};

export default meta;
type Story = StoryObj;

const employees = [
  { id: 1, name: "Jane Smith", role: "Hygienist", status: "active" },
  { id: 2, name: "Bob Jones", role: "Technician", status: "active" },
  { id: 3, name: "Alice Wu", role: "Supervisor", status: "inactive" },
];

function EmployeeFormDialog() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button size="sm">Add employee</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New employee</DialogTitle>
        </DialogHeader>
        <FieldGroup>
          <Field>
            <FieldLabel>First name</FieldLabel>
            <Input placeholder="Jane" />
          </Field>
          <Field>
            <FieldLabel>Last name</FieldLabel>
            <Input placeholder="Smith" />
          </Field>
          <Field>
            <FieldLabel>Title</FieldLabel>
            <Select>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select…" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="mr">Mr.</SelectItem>
                <SelectItem value="ms">Ms.</SelectItem>
                <SelectItem value="dr">Dr.</SelectItem>
              </SelectContent>
            </Select>
          </Field>
          <Field>
            <FieldLabel>Email</FieldLabel>
            <Input type="email" placeholder="jane@example.com" />
          </Field>
          <Field data-invalid="true">
            <FieldLabel>ADP ID</FieldLabel>
            <Input aria-invalid="true" placeholder="ADP-0001" />
            <FieldError>Must match ADP-XXXX format.</FieldError>
          </Field>
          <div className="flex items-center gap-2">
            <Checkbox id="notify" />
            <Label htmlFor="notify">Send welcome email</Label>
          </div>
        </FieldGroup>
        <DialogFooter showCloseButton>
          <Button>Create</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export const AdminPage: Story = {
  name: "Admin page (composite)",
  render: () => (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      {/* top bar */}
      <header className="flex h-10 items-center justify-between border-b px-4">
        <span className="text-xs font-medium">SCA IH Tracker</span>
        <div className="flex items-center gap-2">
          <Badge variant="outline">admin</Badge>
          <Button variant="ghost" size="xs">
            Sign out
          </Button>
        </div>
      </header>

      <div className="flex flex-1">
        {/* sidebar */}
        <nav className="flex w-48 flex-col gap-1 border-r p-2">
          {["Dashboard", "Schools", "Employees", "Contractors"].map((item) => (
            <button
              key={item}
              className="rounded-none px-2 py-1.5 text-left text-xs hover:bg-muted"
            >
              {item}
            </button>
          ))}
        </nav>

        {/* main */}
        <main className="flex flex-1 flex-col gap-6 p-6">
          {/* stat cards */}
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Schools", count: 42 },
              { label: "Employees", count: 18 },
              { label: "Projects", count: 7 },
            ].map(({ label, count }) => (
              <Card key={label}>
                <CardHeader>
                  <CardTitle>{label}</CardTitle>
                  <CardDescription>Active records</CardDescription>
                </CardHeader>
                <CardContent className="text-2xl font-medium">
                  {count}
                </CardContent>
              </Card>
            ))}
          </div>

          <Separator />

          {/* employees section */}
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-medium">Employees</h2>
              <EmployeeFormDialog />
            </div>

            <Tabs defaultValue="list">
              <TabsList>
                <TabsTrigger value="list">List</TabsTrigger>
                <TabsTrigger value="loading">Loading</TabsTrigger>
              </TabsList>

              <TabsContent value="list">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {employees.map((emp) => (
                      <TableRow key={emp.id}>
                        <TableCell>{emp.name}</TableCell>
                        <TableCell>{emp.role}</TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              emp.status === "active" ? "default" : "outline"
                            }
                          >
                            {emp.status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TabsContent>

              <TabsContent value="loading" className="flex flex-col gap-2 pt-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </TabsContent>
            </Tabs>

            {/* notes textarea */}
            <Field>
              <FieldLabel>Internal note</FieldLabel>
              <Textarea rows={3} placeholder="Add a note about this batch…" />
            </Field>
          </div>
        </main>
      </div>
    </div>
  ),
};
