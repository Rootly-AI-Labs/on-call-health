"use client"

import { useMemo } from "react"
import { BaseRiskFactorsCard } from "./BaseRiskFactorsCard"
import { FACTOR_DESCRIPTIONS } from "./TeamRiskFactorsCard"

interface UserRiskFactorsCardProps {
  selectedMember: {
    user_name?: string
    factors?: {
      workload?: number
      afterHours?: number
      weekendWork?: number
      incidentLoad?: number
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
    return [
      {
        factor: 'Workload Intensity',
        value: (factorData.workload || 0) * 10  // Normalize from [0, 10] to [0, 100]
      },
      {
        factor: 'After Hours Activity',
        value: (factorData.afterHours || 0) * 10
      },
      {
        factor: 'Weekend Work',
        value: (factorData.weekendWork || 0) * 10
      },
      {
        factor: 'Incident Load',
        value: (factorData.incidentLoad || 0) * 10
      },
      {
        factor: 'Response Time',
        value: (factorData.responseTime || 0) * 10
      }
    ].filter(f => f.value > 0)  // Only show factors with data
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
