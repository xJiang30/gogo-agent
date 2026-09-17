import type { TripDay, TripNode } from '../model'

type RouteCanvasProps = {
  day: TripDay
  selectedNodeId: string
  onSelectNode: (nodeId: string) => void
}

export function RouteCanvas({
  day,
  selectedNodeId,
  onSelectNode,
}: RouteCanvasProps) {
  const points = day.nodes
    .map((node) => `${node.position.x},${node.position.y}`)
    .join(' ')

  return (
    <section className="route-canvas" aria-label={`${day.label} 路线图`}>
      <div className="route-canvas__grid" />
      <svg className="route-canvas__line" viewBox="0 0 100 100" aria-hidden>
        <polyline points={points} fill="none" />
      </svg>
      {day.nodes.map((node) => (
        <RouteNode
          isSelected={node.id === selectedNodeId}
          key={node.id}
          node={node}
          onSelectNode={onSelectNode}
        />
      ))}
    </section>
  )
}

type RouteNodeProps = {
  node: TripNode
  isSelected: boolean
  onSelectNode: (nodeId: string) => void
}

function RouteNode({ node, isSelected, onSelectNode }: RouteNodeProps) {
  return (
    <button
      className={`route-node route-node--${node.kind} ${
        isSelected ? 'is-selected' : ''
      }`}
      style={{
        left: `${node.position.x}%`,
        top: `${node.position.y}%`,
      }}
      type="button"
      onClick={() => onSelectNode(node.id)}
    >
      <span className="route-node__dot" />
      <span className="route-node__label">
        <strong>{node.time}</strong>
        {node.title}
      </span>
    </button>
  )
}
