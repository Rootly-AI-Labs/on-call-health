import assert from 'node:assert/strict'
import { test } from 'node:test'
import { getVisibleOCHFactors } from './riskFactorUtils'

test('saved analyses hide meeting load before selecting the top five factors', () => {
  const currentFactors = [
    ['after_hours_activity', 'After-hours activity'],
    ['sleep_quality_proxy', 'High-severity incidents'],
    ['oncall_burden', 'On-call load'],
    ['work_hours_trend', 'Task load'],
    ['sprint_completion', 'Consecutive incident days'],
    ['alert_health', 'Alert health & burden'],
  ].map(([key, name], index) => ({ key, name, percentage: 20 - index }))
  const storedFactors = [
    { key: 'meeting_load', name: 'Meeting load', percentage: 30 },
    ...currentFactors,
  ]
  const snapshot = structuredClone(storedFactors)

  const visible = getVisibleOCHFactors(storedFactors)

  assert.deepEqual(visible, currentFactors)
  assert.deepEqual(visible.slice(0, 5), currentFactors.slice(0, 5))
  assert.deepEqual(storedFactors, snapshot)
})

test('older labels and empty results cannot surface meeting load', () => {
  assert.deepEqual(getVisibleOCHFactors([{ name: 'Meeting load' }]), [])
  assert.deepEqual(getVisibleOCHFactors([{ key: 'meeting_load' }]), [])
  assert.deepEqual(getVisibleOCHFactors(undefined), [])
  assert.deepEqual(getVisibleOCHFactors(null), [])
  assert.deepEqual(getVisibleOCHFactors([]), [])
})
