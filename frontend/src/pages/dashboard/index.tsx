import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function DashboardPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <Card className="max-w-md">
        <CardHeader>
          <CardTitle>Coming soon</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            The manager dashboard is under construction. View your projects in
            the meantime.
          </p>
          <Button asChild>
            <Link to="/projects">View Projects</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
