import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "@/test/queryClient";
import { EmployeeRoleTypeDetail } from "./EmployeeRoleTypeDetail";
import type { EmployeeRoleTypeRead } from "@/api/generated/types.gen";
import type * as TanStackRouter from "@tanstack/react-router";

const { mockDelete, mockToastError } = vi.hoisted(() => ({
  mockDelete: vi.fn(),
  mockToastError: vi.fn(),
}));

const SAMPLE_ROLE_TYPE: EmployeeRoleTypeRead = {
  id: 7,
  name: "Mold Field Technician",
  description: "Conducts mold field sampling.",
};

vi.mock("@/features/employee-role-types/api/employeeRoleTypes", () => ({
  getEmployeeRoleTypeOptions: () => ({
    queryKey: ["employee-role-type", 7],
    queryFn: async () => SAMPLE_ROLE_TYPE,
  }),
  getEmployeeRoleTypeQueryKey: () => ["employee-role-type", 7],
  listEmployeeRoleTypesQueryKey: () => ["employee-role-types"],
  deleteEmployeeRoleTypeMutation: () => ({ mutationFn: mockDelete }),
  createEmployeeRoleTypeMutation: () => ({ mutationFn: vi.fn() }),
  updateEmployeeRoleTypeMutation: () => ({ mutationFn: vi.fn() }),
}));

vi.mock("sonner", () => ({
  toast: { error: mockToastError, success: vi.fn() },
}));

vi.mock("@tanstack/react-router", async (importOriginal) => {
  const actual = await importOriginal<typeof TanStackRouter>();
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    Link: ({
      children,
      ...props
    }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { to?: string }) => (
      <a href={props.to ?? "#"}>{children}</a>
    ),
  };
});

function renderDetail() {
  const client = createTestQueryClient();
  return render(
    <QueryClientProvider client={client}>
      <EmployeeRoleTypeDetail roleTypeId={7} />
    </QueryClientProvider>,
  );
}

describe("EmployeeRoleTypeDetail", () => {
  it("409 delete renders inline error and does not call toast.error", async () => {
    mockDelete.mockRejectedValue({
      detail: "Employee role type is in use by active employee roles.",
    });

    renderDetail();

    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findAllByText("Mold Field Technician");

    await user.click(screen.getByRole("button", { name: /delete/i }));
    await user.click(screen.getByRole("button", { name: /^delete$/i }));

    await waitFor(() => {
      expect(
        screen.getByText(
          "Employee role type is in use by active employee roles.",
        ),
      ).toBeInTheDocument();
    });

    expect(mockToastError).not.toHaveBeenCalled();
  });
});
