import { SignOutIcon, UserIcon } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useAuthStore } from "@/auth/store";
import { useAdminShellStore } from "@/lib/admin-shell-state";

export function AdminTopBar() {
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const pageTitle = useAdminShellStore((s) => s.pageTitle);
  const pageActions = useAdminShellStore((s) => s.pageActions);

  return (
    <header className="flex h-14 flex-shrink-0 items-center justify-between border-b bg-background px-6">
      <div className="flex items-center gap-4">
        {pageTitle != null && (
          <h1 className="text-base font-semibold">{pageTitle}</h1>
        )}
        {pageActions != null && (
          <div className="flex items-center gap-2">{pageActions}</div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <ThemeToggle />
        {user && (
          <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <UserIcon size={15} />
            {user.username}
          </span>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={clearAuth}
          className="flex items-center gap-1.5"
        >
          <SignOutIcon size={15} />
          Sign out
        </Button>
      </div>
    </header>
  );
}
