import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function AdminOverviewPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Admin</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Schools</CardTitle>
          </CardHeader>
          <CardContent>
            <Button asChild size="sm">
              <Link to="/admin/schools">Manage Schools</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
