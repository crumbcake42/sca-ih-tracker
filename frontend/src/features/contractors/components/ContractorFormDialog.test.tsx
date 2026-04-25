import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "@/test/queryClient";
import { ContractorFormDialog } from "./ContractorFormDialog";
import type { Contractor } from "@/api/generated/types.gen";

const { mockCreate, mockUpdate, mockToastError } = vi.hoisted(() => ({
  mockCreate: vi.fn(),
  mockUpdate: vi.fn(),
  mockToastError: vi.fn(),
}));

vi.mock("@/features/contractors/api/contractors", () => ({
  createContractorMutation: () => ({ mutationFn: mockCreate }),
  updateContractorMutation: () => ({ mutationFn: mockUpdate }),
  listContractorsQueryKey: () => ["contractors"],
  getContractorQueryKey: () => ["contractor"],
}));

vi.mock("sonner", () => ({
  toast: { error: mockToastError, success: vi.fn() },
}));

const SAMPLE_CONTRACTOR: Contractor = {
  id: 5,
  name: "Acme Corp",
  address: "123 Main St",
  city: "Brooklyn",
  state: "NY",
  zip_code: "11201",
};

function renderDialog(
  props: Partial<React.ComponentProps<typeof ContractorFormDialog>> = {},
) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <ContractorFormDialog open={true} onOpenChange={vi.fn()} {...props} />
    </QueryClientProvider>,
  );
}

describe("ContractorFormDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("create path: calls mockCreate with correct body", async () => {
    mockCreate.mockResolvedValue({});

    renderDialog();

    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await user.type(screen.getByLabelText(/^name$/i), "Test Contractor");
    await user.type(screen.getByLabelText(/address/i), "456 Oak Ave");
    await user.type(screen.getByLabelText(/city/i), "Manhattan");
    await user.type(screen.getByLabelText(/state/i), "NY");
    await user.type(screen.getByLabelText(/zip code/i), "10001");

    await user.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          body: expect.objectContaining({
            name: "Test Contractor",
            address: "456 Oak Ave",
            city: "Manhattan",
            state: "NY",
            zip_code: "10001",
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

    await user.type(screen.getByLabelText(/^name$/i), "Duplicate Name");
    await user.type(screen.getByLabelText(/address/i), "789 Elm St");
    await user.type(screen.getByLabelText(/city/i), "Queens");
    await user.type(screen.getByLabelText(/state/i), "NY");
    await user.type(screen.getByLabelText(/zip code/i), "11101");

    await user.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(screen.getByText("Name already exists.")).toBeInTheDocument();
    });

    expect(mockToastError).not.toHaveBeenCalled();
  });

  it("edit mode: prefills fields from contractor prop", async () => {
    mockUpdate.mockResolvedValue({});

    renderDialog({ contractor: SAMPLE_CONTRACTOR });

    expect(screen.getByDisplayValue("Acme Corp")).toBeInTheDocument();
    expect(screen.getByDisplayValue("123 Main St")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Brooklyn")).toBeInTheDocument();
  });
});
