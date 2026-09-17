import type { PlanningProject } from '../model'

type ProjectListProps = {
  projects: PlanningProject[]
  selectedProjectId: string
  onSelectProject: (projectId: string) => void
}

export function ProjectList({
  projects,
  selectedProjectId,
  onSelectProject,
}: ProjectListProps) {
  return (
    <aside className="project-list" aria-label="旅行项目">
      <header>
        <div className="brand-mark">G</div>
        <div>
          <p className="ui-kicker">Gogo Agent</p>
          <h1>旅行项目</h1>
        </div>
      </header>
      <div className="project-list__items">
        {projects.map((project) => (
          <button
            className={project.id === selectedProjectId ? 'is-active' : ''}
            key={project.id}
            type="button"
            onClick={() => onSelectProject(project.id)}
          >
            <span>
              <strong>{project.title}</strong>
              <small>{project.updatedAt}</small>
            </span>
            <em>{statusLabel[project.status]}</em>
          </button>
        ))}
      </div>
    </aside>
  )
}

const statusLabel: Record<PlanningProject['status'], string> = {
  collecting: '继续聊',
  ready_to_start: '可开始',
  board_created: 'Trip Board',
}
