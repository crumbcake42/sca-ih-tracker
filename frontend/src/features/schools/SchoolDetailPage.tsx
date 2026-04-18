import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { ArrowLeftIcon } from '@phosphor-icons/react'
import { getSchoolSchoolsIdentifierGetOptions } from '@/api/generated/@tanstack/react-query.gen'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

interface Props {
  schoolId: string
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline gap-4 py-2 border-b last:border-0">
      <dt className="w-28 shrink-0 text-sm    text-muted-foreground">
        {label}
      </dt>
      <dd className="text-sm">{value}</dd>
    </div>
  )
}

export function SchoolDetailPage({ schoolId }: Props) {
  const {
    data: school,
    isLoading,
    error,
  } = useQuery(
    getSchoolSchoolsIdentifierGetOptions({ path: { identifier: schoolId } }),
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/admin/schools">
            <ArrowLeftIcon size={15} />
            Schools
          </Link>
        </Button>
        {school && <h1 className="text-2xl font-semibold">{school.name}</h1>}
      </div>

      <Card className="max-w-lg">
        <CardContent className="pt-4">
          {isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-6 w-full" />
              ))}
            </div>
          )}
          {error && (
            <p className="text-sm text-destructive">
              Could not load school details.
            </p>
          )}
          {school && (
            <dl>
              <DetailRow label="Code" value={school.code} />
              <DetailRow label="Name" value={school.name} />
              <DetailRow label="Address" value={school.address} />
              <DetailRow label="Borough" value={school.city} />
              <DetailRow label="State" value={school.state} />
              <DetailRow label="Zip" value={school.zip_code} />
            </dl>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
