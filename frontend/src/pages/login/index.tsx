import { getRouteApi, useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { useLogin } from "@/features/auth/api/hooks";
import { LoginForm } from "@/features/auth/components/LoginForm";
import type { LoginFormValues } from "@/features/auth/components/LoginForm";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const routeApi = getRouteApi("/login");

export function LoginPage() {
  const navigate = useNavigate();
  const search = routeApi.useSearch();
  const login = useLogin();

  async function onSubmit(values: LoginFormValues) {
    try {
      await login.mutateAsync(values);
      await navigate({ to: search.redirect ?? "/" });
    } catch {
      toast.error("Invalid username or password");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-center text-xl">SCA IH Tracker</CardTitle>
        </CardHeader>
        <CardContent>
          <LoginForm onSubmit={onSubmit} isPending={login.isPending} />
        </CardContent>
      </Card>
    </div>
  );
}
