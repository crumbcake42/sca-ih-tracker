import type { Icon } from "@phosphor-icons/react";
import {
  SquaresFourIcon,
  GraduationCapIcon,
  UsersIcon,
  FolderOpenIcon,
  HardHatIcon,
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
  { label: "Contractors", Icon: HardHatIcon, disabled: true },
];
