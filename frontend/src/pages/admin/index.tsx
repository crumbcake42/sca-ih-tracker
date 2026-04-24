import { Link } from "@tanstack/react-router";
import {
  GraduationCapIcon,
  UsersIcon,
  FolderOpenIcon,
  HardHatIcon,
  UserCheckIcon,
  TagIcon,
  PackageIcon,
  UserCircleIcon,
  ShieldIcon,
  FlaskIcon,
} from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AdminShell } from "./components/AdminShell";
import { cn } from "@/lib/utils";

type EntityCard =
  | {
      label: string;
      description: string;
      Icon: React.ComponentType<{ size?: number; className?: string }>;
      to: string;
      disabled?: false;
    }
  | {
      label: string;
      description: string;
      Icon: React.ComponentType<{ size?: number; className?: string }>;
      disabled: true;
    };

const ENTITY_CARDS: readonly EntityCard[] = [
  {
    label: "Schools",
    description: "View and import school records used across all projects.",
    Icon: GraduationCapIcon,
    to: "/admin/schools",
  },
  {
    label: "Employees",
    description: "Manage employee records, titles, and role assignments.",
    Icon: UsersIcon,
    to: "/admin/employees",
  },
  {
    label: "Projects",
    description: "Create and manage projects. Coming in Phase 3.",
    Icon: FolderOpenIcon,
    disabled: true,
  },
  {
    label: "Contractors",
    description: "Manage contractor records. Coming in Phase 2.3.",
    Icon: HardHatIcon,
    disabled: true,
  },
  {
    label: "Hygienists",
    description: "Manage certified hygienist records. Coming in Phase 2.3.",
    Icon: UserCheckIcon,
    disabled: true,
  },
  {
    label: "WA Codes",
    description:
      "Manage work authorization code categories used on project WAs. Coming in Phase 2.3.",
    Icon: TagIcon,
    disabled: true,
  },
  {
    label: "Deliverables",
    description:
      "Manage deliverable templates and trigger configurations. Coming in Phase 2.3.",
    Icon: PackageIcon,
    disabled: true,
  },
  {
    label: "Users",
    description: "Manage system user accounts and password resets. Coming in Phase 2.4.",
    Icon: UserCircleIcon,
    disabled: true,
  },
  {
    label: "User Roles",
    description:
      "Manage system roles and their permission sets. Coming in Phase 2.4.",
    Icon: ShieldIcon,
    disabled: true,
  },
  {
    label: "Sample Type Config",
    description:
      "Manage sample types, subtypes, unit types, and turnaround options. Coming in Phase 2.5.",
    Icon: FlaskIcon,
    disabled: true,
  },
];

export function AdminOverviewPage() {
  return (
    <>
      <AdminShell.Title>Dashboard</AdminShell.Title>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {ENTITY_CARDS.map((card) => (
          <Card key={card.label} className={cn(card.disabled && "opacity-50")}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <card.Icon size={18} className="text-muted-foreground" />
                {card.label}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                {card.description}
              </p>
              {!card.disabled && (
                <Button size="sm" asChild>
                  <Link to={card.to as never}>Manage {card.label}</Link>
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
