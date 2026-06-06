import type { Agent } from '../types'

export function formatAgentSlugLabel(agent: Agent): string {
  const slug = agent.slug ?? agent.id
  return slug.replace(/-/g, ' ').toUpperCase()
}
