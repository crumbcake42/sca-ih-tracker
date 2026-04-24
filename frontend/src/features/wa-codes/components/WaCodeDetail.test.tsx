import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "@/test/queryClient";
import { WaCodeDetail } from "./WaCodeDetail";
import type { WaCode } from "@/api/generated/types.gen";
import type * as TanStackRouter from "@tanstack/react-router";

const { mockDelete, mockToastError } = vi.hoisted(() => ({
  mockDelete: vi.fn(),
  mockToastError: vi.fn(),
}));

const SAMPLE_WA_CODE: WaCode = {
  id: 10,
  code: "MOLD-01",
  description: "Bulk mold sampling",
  level: "project",
  default_fee: null,
};

vi.mock("@/features/wa-codes/api/wa-codes", () => ({
  getWaCodeOptions: () => ({
    queryKey: ["wa-code", 10],
    queryFn: async () => SAMPLE_WA_CODE,
  }),
  getWaCodeQueryKey: () => ["wa-code", 10],
  listWaCodesQueryKey: () => ["wa-codes"],
  deleteWaCodeMutation: () => ({ mutationFn: mockDelete }),
  // Form dialog calls these when edit opens; stub them so no crash
  getWaCodeConnectionsOptions: () => ({
    queryKey: ["wa-code-connections"],
    queryFn: async () => ({}),
  }),
  createWaCodeMutation: () => ({ mutationFn: vi.fn() }),
  updateWaCodeMutation: () => ({ mutationFn: vi.fn() }),
}));

vi.mock("sonner", () => ({
  toast: { error: mockToastError, success: vi.fn() },
}));

// TanStack Router hooks used by WaCodeDetail
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
      <WaCodeDetail waCodeId={10} />
    </QueryClientProvider>,
  );
}

describe("WaCodeDetail", () => {
  it("409 delete renders inline error and does not call toast.error", async () => {
    mockDelete.mockRejectedValue({
      detail: "WA code is in use by work auths.",
    });

    renderDetail();

    const user = userEvent.setup({ pointerEventsCheck: 0 });

    // Wait for the detail to load (code appears in both h1 and detail row).
    await screen.findAllByText("MOLD-01");

    await user.click(screen.getByRole("button", { name: /delete/i }));

    // Confirm in the dialog.
    await user.click(screen.getByRole("button", { name: /^delete$/i }));

    await waitFor(() => {
      expect(
        screen.getByText("WA code is in use by work auths."),
      ).toBeInTheDocument();
    });

    expect(mockToastError).not.toHaveBeenCalled();
  });
});
