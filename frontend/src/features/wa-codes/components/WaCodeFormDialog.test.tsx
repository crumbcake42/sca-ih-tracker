import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "@/test/queryClient";
import { WaCodeFormDialog } from "./WaCodeFormDialog";
import type { WaCode } from "@/api/generated/types.gen";

const { mockCreate, mockUpdate, mockToastError, mockConnections } = vi.hoisted(
  () => ({
    mockCreate: vi.fn(),
    mockUpdate: vi.fn(),
    mockToastError: vi.fn(),
    mockConnections: vi.fn(),
  }),
);

vi.mock("@/features/wa-codes/api/wa-codes", () => ({
  createWaCodeMutation: () => ({ mutationFn: mockCreate }),
  updateWaCodeMutation: () => ({ mutationFn: mockUpdate }),
  listWaCodesQueryKey: () => ["wa-codes"],
  getWaCodeQueryKey: () => ["wa-code"],
  getWaCodeConnectionsOptions: () => ({
    queryKey: ["wa-code-connections"],
    queryFn: mockConnections,
  }),
}));

vi.mock("sonner", () => ({
  toast: { error: mockToastError, success: vi.fn() },
}));

const SAMPLE_WA_CODE: WaCode = {
  id: 10,
  code: "MOLD-01",
  description: "Bulk mold sampling",
  level: "project",
  default_fee: null,
};

function renderDialog(
  props: Partial<React.ComponentProps<typeof WaCodeFormDialog>> = {},
) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <WaCodeFormDialog open={true} onOpenChange={vi.fn()} {...props} />
    </QueryClientProvider>,
  );
}

describe("WaCodeFormDialog", () => {
  it("create path: calls mockCreate with correct body", async () => {
    mockCreate.mockResolvedValue({});

    renderDialog();

    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await user.type(screen.getByLabelText(/^code$/i), "AIR-02");
    await user.type(
      screen.getByLabelText(/description/i),
      "Air sampling — bulk",
    );

    // Level defaults to Project; leave it.

    await user.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          body: expect.objectContaining({
            code: "AIR-02",
            description: "Air sampling — bulk",
            level: "project",
            default_fee: null,
          }),
        }),
        expect.anything(),
      );
    });
  });

  it("422 → applyServerErrors: attaches error to code field, no toast", async () => {
    mockCreate.mockRejectedValue({
      detail: [
        {
          loc: ["body", "code"],
          msg: "Code already exists.",
          type: "value_error",
        },
      ],
    });

    renderDialog();

    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await user.type(screen.getByLabelText(/^code$/i), "DUP-01");
    await user.type(screen.getByLabelText(/description/i), "Duplicate code");

    await user.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(screen.getByText("Code already exists.")).toBeInTheDocument();
    });

    expect(mockToastError).not.toHaveBeenCalled();
  });

  it("level disabled when connections present", async () => {
    mockConnections.mockResolvedValue({ work_auths: 2, sample_types: 0 });

    renderDialog({ waCode: SAMPLE_WA_CODE });

    // Wait for the connections query to resolve and levelLocked to take effect.
    await waitFor(() => {
      expect(screen.getByText(/in use — level locked/i)).toBeInTheDocument();
    });

    // The Select trigger for Level should be disabled.
    expect(screen.getByRole("combobox", { name: /level/i })).toBeDisabled();
  });
});
