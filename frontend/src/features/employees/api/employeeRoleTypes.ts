import type { EmployeeRoleType } from "@/api/generated/types.gen";

/** Employee role type values keyed by short name.
 * Derived from the backend-generated EmployeeRoleType union — this is the single
 * point of connection. If the backend union changes, TypeScript will error here. */
export const EMPLOYEE_ROLE_TYPES = {
  AsbTechAirTesting: "Asbestos On Site Technical Air Testing",
  AsbProjectMonitor: "Asbestos Project Monitor",
  AsbInspectorA: "Asbestos Inspector Level A",
  AsbInvestigatorA: "Asbestos Investigator Level A",
  AsbProjectManagerA: "Asbestos Project Manager Level A",
  LeadInspectorA: "Certified Lead Inspector / Risk Assessor Level A",
  LeadInspectorB: "Certified Lead Inspector / Risk Assessor Level B",
  MoldFieldTech: "Mold Field Technician",
  MoldProjectManagerA: "Mold Project Manager Level A",
  MoldProjectManagerB: "Mold Project Manager Level B",
} as const satisfies Record<string, EmployeeRoleType>;
