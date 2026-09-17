import type { TripBoard, TripDay } from '../model'

type BoardHeaderProps = {
  board: TripBoard
  activeDay: TripDay
  onSelectDay: (dayId: string) => void
}

export function BoardHeader({
  board,
  activeDay,
  onSelectDay,
}: BoardHeaderProps) {
  return (
    <header className="board-header">
      <div>
        <p className="ui-kicker">{board.destination}</p>
        <h1>{board.title}</h1>
      </div>
      <nav className="day-tabs" aria-label="选择行程日期">
        {board.days.map((day) => (
          <button
            className={day.id === activeDay.id ? 'is-active' : ''}
            key={day.id}
            type="button"
            onClick={() => onSelectDay(day.id)}
          >
            <span>{day.label}</span>
            <small>{day.date}</small>
          </button>
        ))}
      </nav>
    </header>
  )
}
