import type { IntakeFields, IntakeMessage, IntakeStatus } from '../intake/model'

export type PlanningProject = {
  id: string
  title: string
  status: IntakeStatus
  intake: IntakeFields
  chatSessionId: string
  tripBoardId?: string
  updatedAt: string
  messages: IntakeMessage[]
}
