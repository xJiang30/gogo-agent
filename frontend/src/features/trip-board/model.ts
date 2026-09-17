export type TripNodeKind = 'transport' | 'hotel' | 'meal' | 'place'

export type TripNode = {
  id: string
  kind: TripNodeKind
  time: string
  title: string
  location: string
  duration: string
  detail: string
  booked: boolean
  position: {
    x: number
    y: number
  }
}

export type TripDay = {
  id: string
  label: string
  date: string
  title: string
  nodes: TripNode[]
}

export type TripBoard = {
  id: string
  title: string
  destination: string
  days: TripDay[]
}
