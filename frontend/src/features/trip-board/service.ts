import { mockTripBoards } from './mock'
import type { TripBoard } from './model'

export async function listTripBoards(): Promise<TripBoard[]> {
  return mockTripBoards
}

export async function getTripBoard(id: string): Promise<TripBoard | undefined> {
  return mockTripBoards.find((board) => board.id === id)
}
