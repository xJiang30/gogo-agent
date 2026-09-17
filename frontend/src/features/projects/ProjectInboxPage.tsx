import { useEffect, useMemo, useState } from 'react'
import { getTripBoard } from '../trip-board/service'
import type { TripBoard } from '../trip-board/model'
import { TripBoardPage } from '../trip-board/TripBoardPage'
import { ProjectHome } from './components/ProjectHome'
import { ProjectList } from './components/ProjectList'
import type { PlanningProject } from './model'
import { listPlanningProjects } from './service'

export function ProjectInboxPage() {
  const [projects, setProjects] = useState<PlanningProject[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState('')
  const [activeBoard, setActiveBoard] = useState<TripBoard | null>(null)

  useEffect(() => {
    void listPlanningProjects().then((items) => {
      setProjects(items)
      setSelectedProjectId(items[0]?.id ?? '')
    })
  }, [])

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId),
    [projects, selectedProjectId],
  )

  async function handleOpenTripBoard(tripBoardId: string) {
    const board = await getTripBoard(tripBoardId)
    if (board) {
      setActiveBoard(board)
    }
  }

  if (activeBoard && selectedProject) {
    return (
      <TripBoardPage
        board={activeBoard}
        onBackToProjects={() => setActiveBoard(null)}
        project={selectedProject}
      />
    )
  }

  return (
    <main className="project-inbox">
      <ProjectList
        onSelectProject={(projectId) => {
          setSelectedProjectId(projectId)
          setActiveBoard(null)
        }}
        projects={projects}
        selectedProjectId={selectedProjectId}
      />
      {selectedProject ? (
        <ProjectHome
          onOpenTripBoard={handleOpenTripBoard}
          project={selectedProject}
        />
      ) : (
        <section className="project-home project-home--empty">
          <p>正在加载项目...</p>
        </section>
      )}
    </main>
  )
}
