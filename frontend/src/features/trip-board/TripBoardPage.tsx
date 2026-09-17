import { useMemo, useState } from 'react'
import { AssistantPanel } from '../assistant/AssistantPanel'
import type { PlanningProject } from '../projects/model'
import { BoardHeader } from './components/BoardHeader'
import { DayTimeline } from './components/DayTimeline'
import { RouteCanvas } from './components/RouteCanvas'
import type { TripBoard } from './model'

type TripBoardPageProps = {
  board: TripBoard
  project: PlanningProject
  onBackToProjects: () => void
}

export function TripBoardPage({
  board,
  project,
  onBackToProjects,
}: TripBoardPageProps) {
  const [activeDayId, setActiveDayId] = useState(board.days[0]?.id ?? '')
  const activeDay = useMemo(
    () => board.days.find((day) => day.id === activeDayId) ?? board.days[0],
    [activeDayId, board.days],
  )
  const [selectedNodeId, setSelectedNodeId] = useState(
    activeDay?.nodes[0]?.id ?? '',
  )
  const [assistantCollapsed, setAssistantCollapsed] = useState(true)
  const selectedNode =
    activeDay?.nodes.find((node) => node.id === selectedNodeId) ??
    activeDay?.nodes[0]

  function handleSelectDay(dayId: string) {
    const nextDay = board.days.find((day) => day.id === dayId)
    setActiveDayId(dayId)
    setSelectedNodeId(nextDay?.nodes[0]?.id ?? '')
    setAssistantCollapsed(true)
  }

  function handleSelectNode(nodeId: string) {
    setSelectedNodeId(nodeId)
    setAssistantCollapsed(false)
  }

  if (!activeDay || !selectedNode) {
    return null
  }

  return (
    <main
      className={`trip-board-page ${
        assistantCollapsed
          ? 'trip-board-page--assistant-collapsed'
          : 'trip-board-page--assistant-open'
      }`}
    >
      <section className="timeline-panel">
        <div className="trip-board-topline">
          <button type="button" className="text-button" onClick={onBackToProjects}>
            返回项目
          </button>
          <span>{project.updatedAt}</span>
        </div>
        <BoardHeader
          activeDay={activeDay}
          board={board}
          onSelectDay={handleSelectDay}
        />
        <DayTimeline
          day={activeDay}
          onSelectNode={handleSelectNode}
          selectedNodeId={selectedNode.id}
        />
      </section>

      <section className="map-panel">
        <header className="map-header">
          <div>
            <p className="ui-kicker">Route sense</p>
            <h2>路线感</h2>
            <span>
              {activeDay.label} · {activeDay.title}
            </span>
          </div>
          <button type="button" className="secondary-button">
            导航
          </button>
        </header>
        <RouteCanvas
          day={activeDay}
          onSelectNode={handleSelectNode}
          selectedNodeId={selectedNode.id}
        />
      </section>

      <AssistantPanel
        isCollapsed={assistantCollapsed}
        onCollapse={() => setAssistantCollapsed(true)}
        onExpand={() => setAssistantCollapsed(false)}
        project={project}
        selectedNode={selectedNode}
      />
    </main>
  )
}
