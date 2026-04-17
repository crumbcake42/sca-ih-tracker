import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { getProjectsProjectsGetOptions } from '../../../api/generated/@tanstack/react-query.gen'
import { Input } from '#/components/ui/input'
import { Skeleton } from '#/components/ui/skeleton'
import { Card, CardContent } from '#/components/ui/card'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '#/components/ui/table'

export const Route = createFileRoute('/_authenticated/projects/')({
  component: ProjectsPage,
})

function ProjectsPage() {
  const [nameSearch, setNameSearch] = useState('')

  const { data: projects, isLoading } = useQuery(
    getProjectsProjectsGetOptions({
      query: { name_search: nameSearch || undefined },
    }),
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <Input
          placeholder="Search projects…"
          value={nameSearch}
          onChange={(e) => setNameSearch(e.target.value)}
          className="w-56"
        />
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Project #</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Schools</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell>
                      <Skeleton className="h-4 w-24" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-48" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-8" />
                    </TableCell>
                  </TableRow>
                ))
              ) : projects?.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={3}
                    className="text-muted-foreground py-8 text-center"
                  >
                    No projects found.
                  </TableCell>
                </TableRow>
              ) : (
                projects?.map((project) => (
                  <TableRow key={project.id}>
                    <TableCell className="font-mono">
                      {project.project_number}
                    </TableCell>
                    <TableCell>{project.name}</TableCell>
                    <TableCell>{project.school_ids?.length ?? 0}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
