import type { Icon } from "@phosphor-icons/react";
import {
  SquaresFourIcon,
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

export type EnabledAdminNavItem = {
  label: string;
  to: string;
  Icon: Icon;
  disabled?: false;
};

export type DisabledAdminNavItem = {
  label: string;
  Icon: Icon;
  disabled: true;
};

export type AdminNavItem = EnabledAdminNavItem | DisabledAdminNavItem;

export const ADMIN_NAV_ITEMS: readonly AdminNavItem[] = [
  { label: "Dashboard", to: "/admin", Icon: SquaresFourIcon },
  { label: "Schools", to: "/admin/schools", Icon: GraduationCapIcon },
  { label: "Employees", to: "/admin/employees", Icon: UsersIcon },
  { label: "Projects", Icon: FolderOpenIcon, disabled: true },
  { label: "Contractors", to: "/admin/contractors", Icon: HardHatIcon },
  { label: "Hygienists", Icon: UserCheckIcon, disabled: true },
  { label: "WA Codes", to: "/admin/wa-codes", Icon: TagIcon },
  { label: "Deliverables", Icon: PackageIcon, disabled: true },
  { label: "Users", Icon: UserCircleIcon, disabled: true },
  { label: "User Roles", Icon: ShieldIcon, disabled: true },
  { label: "Sample Type Config", Icon: FlaskIcon, disabled: true },
];
