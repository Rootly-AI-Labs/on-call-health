"use client"

import { useState } from "react"
import { TrendsCard } from "@/components/dashboard/TrendsCard"

interface ObjectiveDataCardProps {
  currentAnalysis: any
  loadingTrends: boolean
}

export function ObjectiveDataCard({
  currentAnalysis,
  loadingTrends
}: ObjectiveDataCardProps) {
  const [selectedMetric, setSelectedMetric] = useState<string>("health_score")

  // Metric configuration
  const METRIC_CONFIG: any = {
    health_score: {
      label: "Risk Level",
      color: "#7C63D6",
      yAxisLabel: "Risk Level",
      dataKey: "dailyScore",
      showMeanLine: true,
      transformer: (trend: any) => Math.max(0, Math.min(100, 100 - Math.round(trend.overall_score * 10)))
    },
    incident_load: {
      label: "Incident Count",
      color: "#7C63D6",
      yAxisLabel: "Incident Count",
      dataKey: "incidentCount",
      showMeanLine: true,
      transformer: (trend: any) => trend.incident_count || 0
    },
    after_hours: {
      label: "After Hours Activity",
      color: "#7C63D6",
      yAxisLabel: "After Hours Incidents",
      dataKey: "afterHoursCount",
      showMeanLine: true,
      transformer: (trend: any) => trend.after_hours_count || 0
    },
    severity_weighted: {
      label: "Workload Intensity",
      color: "#7C63D6",
      yAxisLabel: "Severity-Weighted Load",
      dataKey: "severityWeightedCount",
      showMeanLine: true,
      transformer: (trend: any) => Math.round(trend.severity_weighted_count || 0)
    }
  }

  // Metric descriptions for the info tooltip
  const METRIC_DESCRIPTIONS: any = {
    health_score: {
      title: "Risk Level",
      description: "Measures the team's overall on-call health based on factors such as incident frequency, after-hours work and severity. Higher scores indicate higher risk of overwork."
    },
    incident_load: {
      title: "Incident Count",
      description: "Total count of incidents handled per day. Counts all incidents regardless of severity or timing."
    },
    after_hours: {
      title: "After Hours Activity",
      description: "Incidents occurring outside business hours (before 9 AM or after 5 PM) or on weekends. Timezone-aware based on each team member's local time."
    },
    severity_weighted: {
      title: "Workload Intensity",
      description: "Measures workload stress by weighting incidents based on their severity level. Higher values indicate more stressful workload."
    }
  }

  // Calculate statistics from daily trends
  const calculateStats = (dailyTrends: any[], metric: string, individualData?: any) => {
    if (!dailyTrends || dailyTrends.length === 0) {
      return { mean: 0, min: 0, max: 0, trend: 'neutral' };
    }

    const config = METRIC_CONFIG[metric];

    const values = dailyTrends.map(d => config.transformer(d));

    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const min = Math.min(...values);
    const max = Math.max(...values);

    // Determine trend: compare first third vs last third
    const third = Math.floor(values.length / 3);
    const firstThirdAvg = values.slice(0, third).reduce((a, b) => a + b, 0) / third;
    const lastThirdAvg = values.slice(-third).reduce((a, b) => a + b, 0) / third;

    // For health score, lower is better; for other metrics, higher is worse
    let trend: string;
    if (metric === 'health_score') {
      trend = lastThirdAvg < firstThirdAvg ? 'improving' : lastThirdAvg > firstThirdAvg ? 'declining' : 'stable';
    } else {
      trend = lastThirdAvg > firstThirdAvg ? 'declining' : lastThirdAvg < firstThirdAvg ? 'improving' : 'stable';
    }

    return { mean, min, max, trend };
  };

  // Calculate 7-day running average
  const calculate7DayRunningAverage = (scores: number[]) => {
    return scores.map((score, index) => {
      // For points with < 7 previous data points, use average up to that point (inclusive)
      // edit running average here
      const windowSize = Math.min(7, index + 1);
      const start = Math.max(0, index - windowSize + 1);
      const window = scores.slice(start, index + 1);
      const average = window.reduce((a, b) => a + b, 0) / window.length;
      return Math.round(average);
    });
  };

  // Aggregate weekend work from individual user data
  const aggregateWeekendWork = (date: string, individualData: any): number => {
    if (!individualData || typeof individualData !== 'object') {
      return 0
    }

    let totalWeekendCount = 0

    try {
      Object.keys(individualData).forEach((userEmail) => {
        const userData = individualData[userEmail]
        if (userData && userData[date]) {
          totalWeekendCount += userData[date].weekend_count || 0
        }
      })
    } catch (error) {
      console.warn('Error aggregating weekend work:', error)
      return 0
    }

    return totalWeekendCount
  };

  // Get chart mode from backend analysis data (default to 'normal')
  const chartMode = currentAnalysis?.analysis_data?.chart_mode || 'normal';

  // Get the chart data
  const getChartData = (metric: string) => {
    const dailyTrends = currentAnalysis?.analysis_data?.daily_trends;
    const individualData = currentAnalysis?.analysis_data?.individual_daily_data;
    const config = METRIC_CONFIG[metric];

    if (!dailyTrends || !Array.isArray(dailyTrends) || dailyTrends.length === 0) {
      return [];
    }

    // Convert daily trends to chart format
    const chartData = dailyTrends.map((trend: any) => {
      let metricValue: number;

      // Special handling for weekend work
      if (metric === 'weekend_work') {
        metricValue = aggregateWeekendWork(trend.date, individualData);
      } else {
        metricValue = config.transformer(trend);
      }

      return {
        date: new Date(trend.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        originalDate: trend.date,
        [config.dataKey]: metricValue,
        // Keep these for tooltip
        incidentCount: trend.incident_count || 0,
        afterHours: trend.after_hours_count || 0,
        membersAtRisk: trend.members_at_risk || 0,
        totalMembers: trend.total_members || 0,
        hasData: trend.incident_count > 0
      };
    });

    // Calculate mean
    const values = chartData.map(d => d[config.dataKey]);
    const mean = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0;

    // Apply running average only for health_score
    let displayValues = values;
    if (chartMode === 'running_average' && metric === 'health_score') {
      displayValues = calculate7DayRunningAverage(values);
    }

    // Add mean and display value
    const dataWithMean = chartData.map((d, index) => ({
      ...d,
      [config.dataKey]: displayValues[index],
      meanScore: Math.round(mean)
    }));

    return dataWithMean;
  };

  const chartData = getChartData(selectedMetric);
  const individualData = currentAnalysis?.analysis_data?.individual_daily_data;
  const stats = calculateStats(
    currentAnalysis?.analysis_data?.daily_trends || [],
    selectedMetric,
    individualData
  );
  const timeRange = currentAnalysis?.time_range || currentAnalysis?.analysis_data?.metadata?.days_analyzed || 30;

  const hasData = chartData.length > 0;
  const description = hasData
    ? `Over the last ${timeRange} days, the average ${METRIC_CONFIG[selectedMetric].yAxisLabel.toLowerCase()} was ${Math.round(stats.mean)}${selectedMetric === 'health_score' ? ' points' : ''}.`
    : "No daily trend data available for this analysis";

  return (
    <TrendsCard
      title="Team Trends"
      description={description}
      chartData={chartData}
      loading={loadingTrends}
      selectedMetric={selectedMetric}
      onMetricChange={setSelectedMetric}
      metricConfig={METRIC_CONFIG}
      metricDescriptions={METRIC_DESCRIPTIONS}
      timeRange={timeRange}
    />
  )
}