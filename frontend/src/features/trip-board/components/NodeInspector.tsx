import type { TripNode } from '../model'

type NodeInspectorProps = {
  node: TripNode
}

export function NodeInspector({ node }: NodeInspectorProps) {
  return (
    <aside className="node-inspector" aria-label="节点详情">
      <p className="ui-kicker">Node detail</p>
      <h2>{node.title}</h2>
      <dl>
        <div>
          <dt>时间</dt>
          <dd>{node.time}</dd>
        </div>
        <div>
          <dt>地点</dt>
          <dd>{node.location}</dd>
        </div>
        <div>
          <dt>时长</dt>
          <dd>{node.duration}</dd>
        </div>
        <div>
          <dt>状态</dt>
          <dd>{node.booked ? '已确认' : '待确认'}</dd>
        </div>
      </dl>
      <p>{node.detail}</p>
    </aside>
  )
}
