import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "@/test/queryClient";
import { EmployeeRoleFormDialog } from "./EmployeeRoleFormDialog";
import type { EmployeeRole } from "@/api/generated/types.gen";

// Hoist mocks so they are available inside vi.mock factories.
const { mockCreate, mockUpdate, mockToastError } = vi.hoisted(() => ({
  mockCreate: vi.fn(),
  mockUpdate: vi.fn(),
  mockToastError: vi.fn(),
}));

vi.mock("@/features/employees/api/employees", () => ({
  createEmployeeRoleMutation: () => ({ mutationFn: mockCreate }),
  updateEmployeeRoleMutation: () => ({ mutationFn: mockUpdate }),
  listEmployeeRolesQueryKey: () => ["employee-roles"],
}));

vi.mock("@/features/employee-role-types/api/employeeRoleTypes", () => ({
  listEmployeeRoleTypesOptions: () => ({
    queryKey: ["role-types"],
    queryFn: async () => [{ id: 5, name: "Mold Field Technician" }],
  }),
}));

vi.mock("sonner", () => ({
  toast: { error: mockToastError, success: vi.fn() },
}));

const SAMPLE_ROLE: EmployeeRole = {
  id: 42,
  employee_id: 1,
  role_type_id: 5,
  role_type: { id: 5, name: "Mold Field Technician" },
  start_date: "2024-01-01",
  end_date: null,
  hourly_rate: "35.00",
};

function renderDialog(
  props: Partial<React.ComponentProps<typeof EmployeeRoleFormDialog>> = {},
) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <EmployeeRoleFormDialog
        open={true}
        onOpenChange={vi.fn()}
        employeeId={1}
        {...props}
      />
    </QueryClientProvider>,
  );
}

describe("EmployeeRoleFormDialog", () => {
  it("disables role_type and start_date in edit mode", () => {
    renderDialog({ role: SAMPLE_ROLE });

    expect(screen.getByRole("combobox", { name: /role type/i })).toBeDisabled();

    expect(screen.getByLabelText(/start date/i)).toBeDisabled();

    // end_date and hourly_rate must remain enabled
    expect(screen.getByLabelText(/end date/i)).not.toBeDisabled();
    expect(screen.getByLabelText(/hourly rate/i)).not.toBeDisabled();
  });

  it("shows inline banner on 409 and does not call toast.error", async () => {
    mockCreate.mockRejectedValue({
      detail: "Date range overlaps an existing role.",
    });

    renderDialog();

    // pointerEventsCheck: 0 skips the pointer-events CSS check — Radix Dialog
    // sets pointer-events:none on <body> for scroll-lock, which jsdom treats as
    // blocking all clicks even though elements inside the dialog are auto.
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    // Wait for role types to load, then select one
    const trigger = await screen.findByRole("combobox", { name: /role type/i });
    await user.click(trigger);
    const option = await screen.findByRole("option", {
      name: "Mold Field Technician",
    });
    await user.click(option);

    await user.clear(screen.getByLabelText(/start date/i));
    await user.type(screen.getByLabelText(/start date/i), "2024-03-01");
    await user.clear(screen.getByLabelText(/hourly rate/i));
    await user.type(screen.getByLabelText(/hourly rate/i), "40");

    await user.click(screen.getByRole("button", { name: /add role/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Date range overlaps an existing role.",
      );
    });

    expect(mockToastError).not.toHaveBeenCalled();
  });

  it("attaches 422 validation error to the end_date field", async () => {
    mockUpdate.mockRejectedValue({
      detail: [
        {
          loc: ["body", "end_date"],
          msg: "end_date must be after start_date",
          type: "value_error",
        },
      ],
    });

    renderDialog({ role: SAMPLE_ROLE });

    const user = userEvent.setup();
    await user.clear(screen.getByLabelText(/end date/i));
    await user.type(screen.getByLabelText(/end date/i), "2023-01-01");

    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(
        screen.getByText("end_date must be after start_date"),
      ).toBeInTheDocument();
    });

    expect(mockToastError).not.toHaveBeenCalled();
  });
});
