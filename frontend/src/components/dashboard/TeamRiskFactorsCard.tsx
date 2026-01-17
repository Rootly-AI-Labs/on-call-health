"use client"

import { BaseRiskFactorsCard } from "./BaseRiskFactorsCard"

export const FACTOR_DESCRIPTIONS: Record<string, { tooltip: string }> = {
  'Workload Intensity': {
    tooltip: 'Measures workload stress by weighting incidents based on their severity level. Higher values indicate more stressful workload.'
  },
  'After Hours Activity': {
    tooltip: 'Work outside business hours (9 AM - 5 PM) and weekends. Timezone-aware based on team member\'s local time.'
  },
  'Incident Load': {
    tooltip: 'Total incident volume and frequency. Counts all incidents regardless of severity or timing.'
  },
  'Weekend Work': {
    tooltip: 'Measures work activity on Saturdays and Sundays.'
  },
  'Response Time': {
    tooltip: 'Measures urgency of response requirements and time pressure.'
  }
}

interface TeamRiskFactorsCardProps {
  factorsData: Array<{ factor: string; value: number }>
  highRiskFactorsCount: number
  description: string | React.ReactNode
  loadingAnalysis?: boolean
  membersCount?: number
}

export function TeamRiskFactorsCard({
  factorsData,
  highRiskFactorsCount,
  description,
  loadingAnalysis = false,
  membersCount = 0
}: TeamRiskFactorsCardProps) {

  return (
    <BaseRiskFactorsCard
      title="Team Risk Factors"
      description={description}
      factorsData={factorsData}
      showAlert={highRiskFactorsCount > 0}
      alertCount={highRiskFactorsCount}
      showInfoTooltip={true}
      factorDescriptions={FACTOR_DESCRIPTIONS}
      domain={[0, 100]}
      height="h-64"
      chartColor="#8b5cf6"
      loading={loadingAnalysis}
    />
  )
}
