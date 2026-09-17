import { mockProjects } from './mock'
import type { PlanningProject } from './model'

export async function listPlanningProjects(): Promise<PlanningProject[]> {
  return mockProjects
}

export async function getPlanningProject(
  id: string,
): Promise<PlanningProject | undefined> {
  return mockProjects.find((project) => project.id === id)
}
