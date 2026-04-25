import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { QueryClientProvider } from "@tanstack/react-query";
import { createTestQueryClient } from "@/test/queryClient";
import { HygienistDetail } from "./HygienistDetail";
import type { Hygienist } from "@/api/generated/types.gen";
import type * as TanStackRouter from "@tanstack/react-router";

const { mockDelete, mockToastError } = vi.hoisted(() => ({
  mockDelete: vi.fn(),
  mockToastError: vi.fn(),
}));

const SAMPLE_HYGIENIST: Hygienist = {
  id: 3,
  first_name: "Jane",
  last_name: "Smith",
  email: "jane@example.com",
  phone: "555-1234",
};

vi.mock("@/features/hygienists/api/hygienists", () => ({
  getHygienistOptions: () => ({
    queryKey: ["hygienist", 3],
    queryFn: async () => SAMPLE_HYGIENIST,
  }),
  getHygienistQueryKey: () => ["hygienist", 3],
  listHygienistsQueryKey: () => ["hygienists"],
  deleteHygienistMutation: () => ({ mutationFn: mockDelete }),
  createHygienistMutation: () => ({ mutationFn: vi.fn() }),
  updateHygienistMutation: () => ({ mutationFn: vi.fn() }),
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
      <HygienistDetail hygienistId={3} />
    </QueryClientProvider>,
  );
}

describe("HygienistDetail", () => {
  it("409 delete renders inline error and does not call toast.error", async () => {
    mockDelete.mockRejectedValue({
      detail: "Hygienist is assigned to active projects.",
    });

    renderDetail();

    const user = userEvent.setup({ pointerEventsCheck: 0 });

    await screen.findAllByText("Jane Smith");

    await user.click(screen.getByRole("button", { name: /delete/i }));
    await user.click(screen.getByRole("button", { name: /^delete$/i }));

    await waitFor(() => {
      expect(
        screen.getByText("Hygienist is assigned to active projects."),
      ).toBeInTheDocument();
    });

    expect(mockToastError).not.toHaveBeenCalled();
  });
});
