import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import { createTestQueryClient } from "@/test/queryClient";
import { useEntityForm } from "./useEntityForm";
import type { UseEntityFormArgs } from "./useEntityForm";
import { z } from "zod";
import type { QueryClient } from "@tanstack/react-query";

// --- Sonner mock ---
const { mockToastError, mockToastSuccess } = vi.hoisted(() => ({
  mockToastError: vi.fn(),
  mockToastSuccess: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: { error: mockToastError, success: mockToastSuccess },
}));

// --- Schema / fixture ---

const schema = z.object({ name: z.string().min(1, "Name is required.") });
type FormValues = z.infer<typeof schema>;

type FakeEntity = { id: number; name: string };
type CreateVars = { body: FormValues };
type UpdateVars = { path: { id: number }; body: FormValues };
type TestArgs = UseEntityFormArgs<
  FakeEntity,
  FormValues,
  CreateVars,
  UpdateVars
>;

const mockCreate = vi.fn();
const mockUpdate = vi.fn();

// Stable module-level references so makeArgs() produces the same function
// identities on every call — avoids TanStack Query's useMutation triggering
// setOptions notifications on each re-render when args are built inside the
// renderHook callback.
const toFormValues = (e: FakeEntity): FormValues => ({ name: e.name });
const buildCreateVars = (values: FormValues): CreateVars => ({ body: values });
const buildUpdateVars = (
  values: FormValues,
  entity: FakeEntity,
): UpdateVars => ({
  path: { id: entity.id },
  body: values,
});
const invalidateKeys = (_entity?: FakeEntity) => [["fake-entities"]];
const CREATE_OPTS = { mutationFn: mockCreate };
const UPDATE_OPTS = { mutationFn: mockUpdate };

function makeArgs(overrides: Partial<TestArgs> = {}): TestArgs {
  return {
    open: true,
    schema,
    defaultValues: { name: "" },
    toFormValues,
    createMutationOptions: CREATE_OPTS,
    updateMutationOptions: UPDATE_OPTS,
    buildCreateVars,
    buildUpdateVars,
    invalidateKeys,
    entityLabel: "Item",
    onSuccess: vi.fn(),
    ...overrides,
  };
}

function wrapper(queryClient: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("useEntityForm", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    mockCreate.mockReset();
    mockUpdate.mockReset();
    mockToastError.mockReset();
    mockToastSuccess.mockReset();
  });

  it("returns isEdit=false when no entity is passed", () => {
    const args = makeArgs();
    const { result } = renderHook(() => useEntityForm(args), {
      wrapper: wrapper(queryClient),
    });
    expect(result.current.isEdit).toBe(false);
  });

  it("returns isEdit=true when an entity is passed", () => {
    const args = makeArgs({ entity: { id: 1, name: "Old" } });
    const { result } = renderHook(() => useEntityForm(args), {
      wrapper: wrapper(queryClient),
    });
    expect(result.current.isEdit).toBe(true);
  });

  it("resets form with entity values when open flips true with an entity", async () => {
    const entity = { id: 1, name: "Old Name" };
    const baseArgs = makeArgs({ entity, open: false });
    const { result, rerender } = renderHook(
      ({ open }: { open: boolean }) => useEntityForm({ ...baseArgs, open }),
      {
        wrapper: wrapper(queryClient),
        initialProps: { open: false },
      },
    );

    rerender({ open: true });

    await waitFor(() => {
      expect(result.current.form.getValues("name")).toBe("Old Name");
    });
  });

  it("calls buildCreateVars and create mutation on submit in create mode", async () => {
    mockCreate.mockResolvedValue({ id: 99, name: "New" });
    const onSuccess = vi.fn();
    const args = makeArgs({ onSuccess });
    const { result } = renderHook(() => useEntityForm(args), {
      wrapper: wrapper(queryClient),
    });

    await act(async () => {
      result.current.form.setValue("name", "New");
      await result.current.form.handleSubmit(result.current.onSubmit)();
    });

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        { body: { name: "New" } },
        expect.anything(),
      );
    });
  });

  it("calls buildUpdateVars and update mutation on submit in edit mode", async () => {
    const entity = { id: 7, name: "Old" };
    mockUpdate.mockResolvedValue({ id: 7, name: "Edited" });
    const onSuccess = vi.fn();
    const args = makeArgs({ entity, onSuccess });
    const { result } = renderHook(() => useEntityForm(args), {
      wrapper: wrapper(queryClient),
    });

    await act(async () => {
      result.current.form.setValue("name", "Edited");
      await result.current.form.handleSubmit(result.current.onSubmit)();
    });

    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledWith(
        { path: { id: 7 }, body: { name: "Edited" } },
        expect.anything(),
      );
    });
  });

  it("attaches 422 field errors and does NOT toast on server error", async () => {
    mockCreate.mockRejectedValue({
      detail: [
        { loc: ["body", "name"], msg: "Too short.", type: "value_error" },
      ],
    });

    const args = makeArgs();
    const { result } = renderHook(
      () => {
        const hookResult = useEntityForm(args);
        // Access errors during render to register the RHF subscription —
        // without this the proxy never triggers a re-render when setError fires.
        void hookResult.form.formState.errors;
        return hookResult;
      },
      { wrapper: wrapper(queryClient) },
    );

    await act(async () => {
      result.current.form.setValue("name", "x");
      await result.current.form.handleSubmit(result.current.onSubmit)();
    });

    await waitFor(() => {
      expect(result.current.form.formState.errors.name?.message).toBe(
        "Too short.",
      );
    });

    expect(mockToastError).not.toHaveBeenCalled();
  });

  it("falls back to toast when error is not a 422 detail array", async () => {
    mockCreate.mockRejectedValue(new Error("Network error"));

    const args = makeArgs();
    const { result } = renderHook(() => useEntityForm(args), {
      wrapper: wrapper(queryClient),
    });

    await act(async () => {
      result.current.form.setValue("name", "x");
      await result.current.form.handleSubmit(result.current.onSubmit)();
    });

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Could not create item.");
    });
  });
});
