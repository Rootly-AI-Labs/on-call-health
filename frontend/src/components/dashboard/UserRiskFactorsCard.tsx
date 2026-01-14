"use client"

import { useMemo } from "react"
import { BaseRiskFactorsCard } from "./BaseRiskFactorsCard"
import { FACTOR_DESCRIPTIONS } from "./TeamRiskFactorsCard"

interface UserRiskFactorsCardProps {
  selectedMember: {
    user_name?: string
    factors?: {
      workload?: number
      after_hours?: number      // Backend returns snake_case
      afterHours?: number       // Frontend may use camelCase
      weekendWork?: number
      incident_load?: number    // Backend returns snake_case
      incidentLoad?: number     // Frontend may use camelCase
      responseTime?: number
    }
  }
  loading?: boolean
}

export function UserRiskFactorsCard({
  selectedMember,
  loading = false
}: UserRiskFactorsCardProps) {

  // Extract and normalize factors from [0, 10] to [0, 100]
  const normalizedFactors = useMemo(() => {
    if (!selectedMember?.factors) {
      return []
    }

    const factorData = selectedMember.factors
    // Handle both snake_case (from backend) and camelCase field names
    const workload = (factorData.workload || 0)
    const afterHours = (factorData.after_hours || factorData.afterHours || 0)
    const incidentLoad = (factorData.incident_load || factorData.incidentLoad || 0)

    return [
      {
        factor: 'Workload Intensity',
        value: workload * 10  // Normalize from [0, 10] to [0, 100]
      },
      {
        factor: 'After Hours Activity',
        value: afterHours * 10
      },
      {
        factor: 'Incident Load',
        value: incidentLoad * 10
      }
    ]  // Always show these 3 factors, even when value is 0
  }, [selectedMember])

  const memberName = selectedMember?.user_name || 'Team Member'

  return (
    <BaseRiskFactorsCard
      title="User Risk Factors"
      description={`Key factors contributing to risk of overwork for ${memberName}`}
      factorsData={normalizedFactors}
      showAlert={false}  // No alert system for individual view
      showInfoTooltip={true}
      factorDescriptions={FACTOR_DESCRIPTIONS}
      domain={[0, 100]}
      height="h-64"
      chartColor="#8b5cf6"
      loading={loading}
    />
  )
}
