import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { cn } from "@/lib/utils";

describe("test infrastructure", () => {
  it("jsdom + RTL + jest-dom are wired up", () => {
    render(<div data-testid="ping">hello</div>);
    expect(screen.getByTestId("ping")).toBeInTheDocument();
  });

  it("@/ path alias resolves", () => {
    expect(cn("a", "b")).toBe("a b");
  });
});
