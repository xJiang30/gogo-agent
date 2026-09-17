import type { PlanningProject } from '../projects/model'
import type { TripNode } from '../trip-board/model'

type AssistantPanelProps = {
  project: PlanningProject
  selectedNode?: TripNode
  isCollapsed?: boolean
  onCollapse?: () => void
  onExpand?: () => void
}

export function AssistantPanel({
  isCollapsed = false,
  onCollapse,
  onExpand,
  project,
  selectedNode,
}: AssistantPanelProps) {
  const isBoardCreated = project.status === 'board_created'

  if (isBoardCreated && isCollapsed) {
    return (
      <aside className="assistant-panel assistant-panel--collapsed">
        <button
          type="button"
          className="assistant-rail"
          onClick={onExpand}
          aria-label="展开 Gogo Agent 助手"
        >
          <span>AI</span>
          <strong>{selectedNode ? selectedNode.title : '选择节点'}</strong>
        </button>
      </aside>
    )
  }

  return (
    <aside className="assistant-panel" aria-label="Gogo Agent 助手">
      <header className="assistant-panel__header">
        <div>
          <p className="ui-kicker">Gogo Agent</p>
          <h2>{isBoardCreated ? '当前节点助手' : '继续规划'}</h2>
        </div>
        {onCollapse ? (
          <button type="button" className="icon-button" onClick={onCollapse}>
            收起
          </button>
        ) : null}
      </header>

      <div className="assistant-panel__body">
        {selectedNode ? (
          <div className="assistant-card">
            <p className="assistant-card__label">选中节点</p>
            <h3>{selectedNode.title}</h3>
            <p>
              {selectedNode.time} · {selectedNode.location} ·{' '}
              {selectedNode.duration}
            </p>
          </div>
        ) : null}

        {project.status === 'board_created' ? (
          <div className="assistant-message">
            我会围绕当前 Day 或节点提建议。比如调整晚餐时间、替换雨天活动，都会先生成
            proposal，等你确认后再应用。
          </div>
        ) : (
          <>
            <div className="assistant-thread">
              {project.messages.map((message) => (
                <div
                  className={`chat-bubble chat-bubble--${message.role}`}
                  key={message.id}
                >
                  <span>{message.content}</span>
                  <time>{message.createdAt}</time>
                </div>
              ))}
            </div>
            <form className="assistant-composer">
              <textarea
                aria-label="继续告诉 Gogo Agent 你的旅行偏好"
                placeholder="继续补充旅行偏好..."
                rows={3}
              />
              <button type="button">发送</button>
            </form>
          </>
        )}

        {selectedNode ? (
          <div className="proposal-card">
            <p>建议把这个节点提前 30 分钟，给后面的移动留出缓冲。</p>
            <div className="proposal-card__actions">
              <button type="button">应用调整</button>
              <button type="button" className="secondary-button">
                再看看
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </aside>
  )
}
