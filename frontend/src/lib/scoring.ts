function clamp100(value: number): number {
  return Math.max(0, Math.min(100, value))
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value)
}

export function getRiskScore100FromMember(member: any): number {
  if (isFiniteNumber(member?.risk_score_100)) return clamp100(member.risk_score_100)
  if (isFiniteNumber(member?.och_score)) return clamp100(member.och_score)
  if (isFiniteNumber(member?.health_score)) return clamp100(member.health_score * 10)
  return 0
}

export function hasMemberRiskScore(member: any): boolean {
  return (
    isFiniteNumber(member?.risk_score_100) ||
    isFiniteNumber(member?.och_score) ||
    isFiniteNumber(member?.health_score)
  )
}

export function getRiskScore100FromTeamHealth(teamHealth: any): number {
  if (!teamHealth) return 0
  if (isFiniteNumber(teamHealth.risk_score_100)) return clamp100(teamHealth.risk_score_100)
  if (isFiniteNumber(teamHealth.health_score_100)) return clamp100(100 - teamHealth.health_score_100)

  const overallScore = teamHealth.overall_score
  if (!isFiniteNumber(overallScore)) return 0

  if (teamHealth.scoring_method === "OCH" || overallScore > 10) {
    return clamp100(overallScore)
  }

  return clamp100(100 - overallScore * 10)
}

export function getRiskScore100FromTrend(trend: any): number {
  if (!trend) return 0
  if (isFiniteNumber(trend.risk_score_100)) return clamp100(trend.risk_score_100)
  if (isFiniteNumber(trend.health_score_100)) return clamp100(100 - trend.health_score_100)

  const overallScore = trend.overall_score
  if (!isFiniteNumber(overallScore)) return 0

  if (trend.overall_score_semantics === "risk_100" || overallScore > 10) {
    return clamp100(overallScore)
  }

  return clamp100(100 - overallScore * 10)
}

export function getRiskScore100FromDailyHealth(day: any): number {
  if (!day) return 0
  if (isFiniteNumber(day.risk_score_100)) return clamp100(day.risk_score_100)

  // Member daily-health payloads still use `health_score` for 0-100 risk.
  if (isFiniteNumber(day.health_score)) return clamp100(day.health_score)
  if (isFiniteNumber(day.health_score_100)) return clamp100(100 - day.health_score_100)
  return 0
}

export function getRiskLevelKey(riskScore100: number): "low" | "mild" | "moderate" | "high" {
  if (riskScore100 < 25) return "low"
  if (riskScore100 < 50) return "mild"
  if (riskScore100 < 75) return "moderate"
  return "high"
}

export function getRiskColor(riskScore100: number): string {
  if (riskScore100 < 25) return "#10B981"
  if (riskScore100 < 50) return "#F59E0B"
  if (riskScore100 < 75) return "#F97316"
  return "#EF4444"
}

export function getRiskStatusLabel(riskScore100: number): "Healthy" | "Fair" | "Poor" | "Critical" {
  if (riskScore100 < 25) return "Healthy"
  if (riskScore100 < 50) return "Fair"
  if (riskScore100 < 75) return "Poor"
  return "Critical"
}

export function getRiskStatusDescription(riskScore100: number): string {
  if (riskScore100 < 25) return "Sustainable workload"
  if (riskScore100 < 50) return "Monitor for trends"
  if (riskScore100 < 75) return "Consider intervention"
  return "Action needed"
}
