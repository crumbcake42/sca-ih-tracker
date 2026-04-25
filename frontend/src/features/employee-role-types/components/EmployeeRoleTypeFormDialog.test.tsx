import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "@/test/queryClient";
import { EmployeeRoleTypeFormDialog } from "./EmployeeRoleTypeFormDialog";
import type { EmployeeRoleTypeRead } from "@/api/generated/types.gen";

const { mockCreate, mockUpdate, mockToastError } = vi.hoisted(() => ({
  mockCreate: vi.fn(),
  mockUpdate: vi.fn(),
  mockToastError: vi.fn(),
}));

vi.mock("@/features/employee-role-types/api/employeeRoleTypes", () => ({
  createEmployeeRoleTypeMutation: () => ({ mutationFn: mockCreate }),
  updateEmployeeRoleTypeMutation: () => ({ mutationFn: mockUpdate }),
  listEmployeeRoleTypesQueryKey: () => ["employee-role-types"],
  getEmployeeRoleTypeQueryKey: () => ["employee-role-type"],
}));

vi.mock("sonner", () => ({
  toast: { error: mockToastError, success: vi.fn() },
}));

const SAMPLE_ROLE_TYPE: EmployeeRoleTypeRead = {
  id: 7,
  name: "Mold Field Technician",
  description: "Conducts mold field sampling.",
};

function renderDialog(
  props: Partial<React.ComponentProps<typeof EmployeeRoleTypeFormDialog>> = {},
) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <EmployeeRoleTypeFormDialog
        open={true}
        onOpenChange={vi.fn()}
        {...props}
      />
    </QueryClientProvider>,
  );
}

describe("EmployeeRoleTypeFormDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("create path: calls mockCreate with correct body", async () => {
    mockCreate.mockResolvedValue({});

    renderDialog();

    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await user.type(screen.getByLabelText(/^name$/i), "Asbestos Inspector");
    await user.type(
      screen.getByLabelText(/description/i),
      "Inspects asbestos on site.",
    );

    await user.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          body: expect.objectContaining({
            name: "Asbestos Inspector",
            description: "Inspects asbestos on site.",
          }),
        }),
        expect.anything(),
      );
    });
  });

  it("required-field validation: blank name blocks submit", async () => {
    renderDialog();

    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await user.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(screen.getByText("Name is required.")).toBeInTheDocument();
    });

    expect(mockCreate).not.toHaveBeenCalled();
  });

  it("422 → applyServerErrors: attaches error to name field, no toast", async () => {
    mockCreate.mockRejectedValue({
      detail: [
        {
          loc: ["body", "name"],
          msg: "Name already exists.",
          type: "value_error",
        },
      ],
    });

    renderDialog();

    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await user.type(screen.getByLabelText(/^name$/i), "Duplicate");

    await user.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(screen.getByText("Name already exists.")).toBeInTheDocument();
    });

    expect(mockToastError).not.toHaveBeenCalled();
  });

  it("edit mode: prefills fields from roleType prop", async () => {
    mockUpdate.mockResolvedValue({});

    renderDialog({ roleType: SAMPLE_ROLE_TYPE });

    expect(
      screen.getByDisplayValue("Mold Field Technician"),
    ).toBeInTheDocument();
    expect(
      screen.getByDisplayValue("Conducts mold field sampling."),
    ).toBeInTheDocument();
  });
});
