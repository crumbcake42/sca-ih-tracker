import { useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { z } from "zod";
import {
  Field,
  FieldLabel,
  FieldError,
  FieldGroup,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const loginSchema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

interface Props {
  onSubmit: (values: LoginFormValues) => Promise<void>;
  isPending: boolean;
}

export function LoginForm({ onSubmit, isPending }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: standardSchemaResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <FieldGroup>
        <Field data-invalid={!!errors.username}>
          <FieldLabel htmlFor="username">Username</FieldLabel>
          <Input
            id="username"
            autoComplete="username"
            aria-invalid={!!errors.username}
            {...register("username")}
          />
          <FieldError errors={[errors.username]} />
        </Field>
        <Field data-invalid={!!errors.password}>
          <FieldLabel htmlFor="password">Password</FieldLabel>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            aria-invalid={!!errors.password}
            {...register("password")}
          />
          <FieldError errors={[errors.password]} />
        </Field>
        <Button type="submit" className="w-full" disabled={isPending}>
          {isPending ? "Signing in…" : "Sign in"}
        </Button>
      </FieldGroup>
    </form>
  );
}
