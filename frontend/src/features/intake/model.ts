export type IntakeFields = {
  destination?: string
  duration?: string
  travelers?: number
  budget?: string
  preferences: string[]
}

export type IntakeMessage = {
  id: string
  role: 'assistant' | 'user'
  content: string
  createdAt: string
}

export type IntakeStatus = 'collecting' | 'ready_to_start' | 'board_created'
