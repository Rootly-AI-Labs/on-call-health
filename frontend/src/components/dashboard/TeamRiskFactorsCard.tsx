"use client"

import { BaseRiskFactorsCard } from "./BaseRiskFactorsCard"

export const FACTOR_DESCRIPTIONS: Record<string, string> = {
  // Team-level factor names
  'Workload Intensity': 'Measures workload stress by weighting incidents based on their severity level. Higher values indicate more stressful workload.',
  'After Hours Activity': 'Work outside business hours (9 AM - 5 PM) and weekends. Timezone-aware based on team member\'s local time.',
  'Incident Load': 'Total incident volume and frequency. Counts all incidents regardless of severity or timing.',
  'Weekend Work': 'Measures work activity on Saturdays and Sundays.',
  'Response Time': 'Measures urgency of response requirements and time pressure.',
  // Individual-level factor names
  'After-hours activity': 'Work outside business hours (9 AM - 5 PM) and weekends. Timezone-aware based on team member\'s local time.',
  'High-severity incidents': 'Count of critical and high-severity incidents handled.',
  'On-call load': 'Total incident volume and frequency during on-call shifts. Counts all incidents regardless of severity.',
  'Task load': 'Number of tasks and tickets assigned. Higher counts indicate more workload pressure.',
  'Consecutive incident days': 'Number of consecutive days with at least one incident. Longer streaks indicate sustained on-call pressure.',
  'Incident frequency': 'Rate of incidents over the analysis period regardless of severity or timing.',
  'Severity-weighted workload': 'Workload score weighted by incident severity. Critical incidents count more than lower severity ones.',
  'Meeting load': 'Volume of meetings and synchronous obligations cutting into focus time.',
  'Review speed pressure': 'How quickly code reviews are expected to be completed, indicating urgency pressure.',
}

interface TeamRiskFactorsCardProps {
  factorsData: Array<{ factor: string; value: number }>
  highRiskFactorsCount: number
  description: string | React.ReactNode
  loadingAnalysis?: boolean
}

export function TeamRiskFactorsCard({
  factorsData,
  highRiskFactorsCount,
  description,
  loadingAnalysis = false
}: TeamRiskFactorsCardProps): React.ReactElement {
  return (
    <BaseRiskFactorsCard
      title="Team Risk Factors"
      description={description}
      factorsData={factorsData}
      showAlert={highRiskFactorsCount > 0}
      alertCount={highRiskFactorsCount}
      factorDescriptions={FACTOR_DESCRIPTIONS}
      loading={loadingAnalysis}
      showInfoTooltip={false}
    />
  )
}
