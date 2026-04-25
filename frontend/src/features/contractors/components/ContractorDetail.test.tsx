import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "@/test/queryClient";
import { ContractorDetail } from "./ContractorDetail";
import type { Contractor } from "@/api/generated/types.gen";
import type * as TanStackRouter from "@tanstack/react-router";

const { mockDelete, mockToastError } = vi.hoisted(() => ({
  mockDelete: vi.fn(),
  mockToastError: vi.fn(),
}));

const SAMPLE_CONTRACTOR: Contractor = {
  id: 5,
  name: "Acme Corp",
  address: "123 Main St",
  city: "Brooklyn",
  state: "NY",
  zip_code: "11201",
};

vi.mock("@/features/contractors/api/contractors", () => ({
  getContractorOptions: () => ({
    queryKey: ["contractor", 5],
    queryFn: async () => SAMPLE_CONTRACTOR,
  }),
  getContractorQueryKey: () => ["contractor", 5],
  listContractorsQueryKey: () => ["contractors"],
  deleteContractorMutation: () => ({ mutationFn: mockDelete }),
  createContractorMutation: () => ({ mutationFn: vi.fn() }),
  updateContractorMutation: () => ({ mutationFn: vi.fn() }),
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
      <ContractorDetail contractorId={5} />
    </QueryClientProvider>,
  );
}

describe("ContractorDetail", () => {
  it("409 delete renders inline error and does not call toast.error", async () => {
    mockDelete.mockRejectedValue({
      detail: "Contractor is linked to active projects.",
    });

    renderDetail();

    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findAllByText("Acme Corp");

    await user.click(screen.getByRole("button", { name: /delete/i }));
    await user.click(screen.getByRole("button", { name: /^delete$/i }));

    await waitFor(() => {
      expect(
        screen.getByText("Contractor is linked to active projects."),
      ).toBeInTheDocument();
    });

    expect(mockToastError).not.toHaveBeenCalled();
  });
});
