import type { TripDay } from '../model'

type DayTimelineProps = {
  day: TripDay
  selectedNodeId: string
  onSelectNode: (nodeId: string) => void
}

export function DayTimeline({
  day,
  selectedNodeId,
  onSelectNode,
}: DayTimelineProps) {
  return (
    <section className="day-timeline" aria-label={`${day.label} 时间线`}>
      <header>
        <p className="ui-kicker">{day.date}</p>
        <h2>{day.title}</h2>
      </header>
      <div className="day-timeline__list">
        {day.nodes.map((node) => (
          <button
            className={`timeline-node-card timeline-node-card--${node.kind} ${
              node.id === selectedNodeId ? 'is-selected' : ''
            }`}
            key={node.id}
            type="button"
            onClick={() => onSelectNode(node.id)}
          >
            <time>{node.time}</time>
            <span className="timeline-node-card__body">
              <span className="timeline-node-card__top">
                <strong>{node.title}</strong>
                <em>{node.booked ? '已确认' : '待确认'}</em>
              </span>
              <small>{node.location}</small>
              <small>
                {node.duration} · {node.detail}
              </small>
            </span>
          </button>
        ))}
      </div>
    </section>
  )
}
