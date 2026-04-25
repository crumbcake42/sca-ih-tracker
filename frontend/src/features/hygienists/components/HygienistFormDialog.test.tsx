import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "@/test/queryClient";
import { HygienistFormDialog } from "./HygienistFormDialog";
import type { Hygienist } from "@/api/generated/types.gen";

const { mockCreate, mockUpdate, mockToastError } = vi.hoisted(() => ({
  mockCreate: vi.fn(),
  mockUpdate: vi.fn(),
  mockToastError: vi.fn(),
}));

vi.mock("@/features/hygienists/api/hygienists", () => ({
  createHygienistMutation: () => ({ mutationFn: mockCreate }),
  updateHygienistMutation: () => ({ mutationFn: mockUpdate }),
  listHygienistsQueryKey: () => ["hygienists"],
  getHygienistQueryKey: () => ["hygienist"],
}));

vi.mock("sonner", () => ({
  toast: { error: mockToastError, success: vi.fn() },
}));

const SAMPLE_HYGIENIST: Hygienist = {
  id: 3,
  first_name: "Jane",
  last_name: "Smith",
  email: "jane@example.com",
  phone: "555-1234",
};

function renderDialog(
  props: Partial<React.ComponentProps<typeof HygienistFormDialog>> = {},
) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <HygienistFormDialog open={true} onOpenChange={vi.fn()} {...props} />
    </QueryClientProvider>,
  );
}

describe("HygienistFormDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("create path: calls mockCreate with correct body", async () => {
    mockCreate.mockResolvedValue({});

    renderDialog();

    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await user.type(screen.getByLabelText(/first name/i), "Alice");
    await user.type(screen.getByLabelText(/last name/i), "Johnson");
    await user.type(screen.getByLabelText(/email/i), "alice@example.com");

    await user.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          body: expect.objectContaining({
            first_name: "Alice",
            last_name: "Johnson",
            email: "alice@example.com",
          }),
        }),
        expect.anything(),
      );
    });
  });

  it("required-field validation: blank first name blocks submit", async () => {
    renderDialog();

    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await user.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(screen.getByText("First name is required.")).toBeInTheDocument();
    });

    expect(mockCreate).not.toHaveBeenCalled();
  });

  it("422 → applyServerErrors: attaches error to first_name field, no toast", async () => {
    mockCreate.mockRejectedValue({
      detail: [
        {
          loc: ["body", "first_name"],
          msg: "First name already exists.",
          type: "value_error",
        },
      ],
    });

    renderDialog();

    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await user.type(screen.getByLabelText(/first name/i), "Duplicate");
    await user.type(screen.getByLabelText(/last name/i), "User");

    await user.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(
        screen.getByText("First name already exists."),
      ).toBeInTheDocument();
    });

    expect(mockToastError).not.toHaveBeenCalled();
  });

  it("edit mode: prefills fields from hygienist prop", async () => {
    mockUpdate.mockResolvedValue({});

    renderDialog({ hygienist: SAMPLE_HYGIENIST });

    expect(screen.getByDisplayValue("Jane")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Smith")).toBeInTheDocument();
    expect(screen.getByDisplayValue("jane@example.com")).toBeInTheDocument();
  });
});
