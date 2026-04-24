import { Link } from "@tanstack/react-router";
import {
  SignOutIcon,
  SignInIcon,
  FolderOpenIcon,
  UserIcon,
  GearIcon,
} from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/auth/store";
import { ThemeToggle } from "@/components/ThemeToggle";

export function AppShell({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.clearAuth);

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b bg-background">
        <div className="mx-auto flex h-14 max-w-screen-xl items-center justify-between px-4">
          <div className="flex items-center gap-6">
            <Link to="/" className="text-sm font-semibold tracking-tight">
              SCA IH Tracker
            </Link>
            <nav className="flex items-center gap-1">
              <Button variant="ghost" size="sm" asChild>
                <Link to="/projects" className="flex items-center gap-1.5">
                  <FolderOpenIcon size={15} />
                  Projects
                </Link>
              </Button>
              {(user?.role.name === "admin" ||
                user?.role.name === "superadmin") && (
                <Button variant="ghost" size="sm" asChild>
                  <Link
                    to="/admin/schools"
                    className="flex items-center gap-1.5"
                  >
                    <GearIcon size={15} />
                    Admin
                  </Link>
                </Button>
              )}
            </nav>
          </div>

          {user ? (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground flex items-center gap-1.5 text-sm">
                <UserIcon size={15} />
                {user?.username}
              </span>
              <ThemeToggle />
              <Button
                variant="ghost"
                size="sm"
                onClick={logout}
                className="flex items-center gap-1.5"
              >
                <SignOutIcon size={15} />
                Sign out
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/login">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={logout}
                  className="flex items-center gap-1.5"
                >
                  <SignInIcon size={15} />
                  Sign In
                </Button>
              </Link>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto w-full max-w-screen-xl flex-1 px-4 py-6">
        {children}
      </main>
    </div>
  );
}
