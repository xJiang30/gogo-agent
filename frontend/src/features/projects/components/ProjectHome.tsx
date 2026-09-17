import { AssistantPanel } from '../../assistant/AssistantPanel'
import type { PlanningProject } from '../model'

type ProjectHomeProps = {
  project: PlanningProject
  onOpenTripBoard: (tripBoardId: string) => void
}

export function ProjectHome({ project, onOpenTripBoard }: ProjectHomeProps) {
  const isBoardCreated = project.status === 'board_created'

  return (
    <section className="project-home" aria-label="项目详情">
      <header className="project-home__header">
        <div>
          <p className="ui-kicker">{statusText[project.status]}</p>
          <h2>{project.title}</h2>
        </div>
        {project.tripBoardId ? (
          <button
            type="button"
            className="primary-button"
            onClick={() => onOpenTripBoard(project.tripBoardId!)}
          >
            进入 Trip Board
          </button>
        ) : null}
      </header>

      <IntakeSummary project={project} />

      {isBoardCreated ? (
        <div className="board-entry">
          <div>
            <p className="ui-kicker">Trip Board ready</p>
            <h3>行程板已创建</h3>
            <p>入口页保留摘要；进入 Trip Board 后继续按 Day 和节点细改。</p>
          </div>
          {project.tripBoardId ? (
            <button
              type="button"
              className="primary-button"
              onClick={() => onOpenTripBoard(project.tripBoardId!)}
            >
              打开
            </button>
          ) : null}
        </div>
      ) : (
        <AssistantPanel project={project} />
      )}
    </section>
  )
}

function IntakeSummary({ project }: { project: PlanningProject }) {
  const fields = [
    ['目的地', project.intake.destination],
    ['时间', project.intake.duration],
    ['同行', project.intake.travelers ? `${project.intake.travelers} 人` : undefined],
    ['预算', project.intake.budget],
    ['偏好', project.intake.preferences.join(' · ')],
  ]

  return (
    <div className="intake-summary">
      {fields.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{value || '待补充'}</strong>
        </div>
      ))}
    </div>
  )
}

const statusText: Record<PlanningProject['status'], string> = {
  collecting: '还在收集信息',
  ready_to_start: '信息够了',
  board_created: '已创建 Trip Board',
}
