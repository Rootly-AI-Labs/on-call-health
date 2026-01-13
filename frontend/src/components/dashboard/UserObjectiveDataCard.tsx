"use client"

import { useState, useEffect, useMemo } from "react"
import { TrendsCard } from "@/components/dashboard/TrendsCard"

interface UserObjectiveDataCardProps {
  memberData: any
  analysisId?: number | string
  timeRange?: number | string
  currentAnalysis?: any
}

export function UserObjectiveDataCard({
  memberData,
  analysisId,
  timeRange = 30,
  currentAnalysis
}: UserObjectiveDataCardProps) {

  const [dailyHealthData, setDailyHealthData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedMetric, setSelectedMetric] = useState<string>("health_score");

  // Metric configuration for dropdown selector
  const METRIC_CONFIG: Record<string, {
    label: string
    color: string
    yAxisLabel: string
    dataKey: string
    showMeanLine: boolean
    transformer: (day: any) => number
  }> = {
    health_score: {
      label: "Risk Level",
      color: "#7C63D6",  // Purple-700
      yAxisLabel: "Risk Level",
      dataKey: "dailyScore",
      showMeanLine: true,
      transformer: (day: any) => day.health_score || 0
    },
    incident_load: {
      label: "Incident Count",
      color: "#7C63D6",  // Purple-700
      yAxisLabel: "Incident Count",
      dataKey: "incidentCount",
      showMeanLine: true,
      transformer: (day: any) => day.incident_count || 0
    },
    after_hours: {
      label: "After Hours Activity",
      color: "#7C63D6",  // Purple-700
      yAxisLabel: "After Hours Incidents",
      dataKey: "afterHoursCount",
      showMeanLine: true,
      transformer: (day: any) => day.after_hours_count || 0
    },
    severity_weighted: {
      label: "Workload Intensity",
      color: "#7C63D6",  // Purple-700
      yAxisLabel: "Severity-Weighted Load",
      dataKey: "severityWeightedCount",
      showMeanLine: true,
      transformer: (day: any) => Math.round(day.severity_weighted_count || 0)
    }
  };

  // Metric descriptions for the info tooltip
  const METRIC_DESCRIPTIONS: any = {
    health_score: {
      title: "Risk Level",
      description: "Measures this member's on-call health based on factors such as incident frequency, after-hours work and severity. Higher scores indicate higher risk of overwork."
    },
    incident_load: {
      title: "Incident Count",
      description: "Total count of incidents handled per day. Counts all incidents regardless of severity or timing."
    },
    after_hours: {
      title: "After Hours Activity",
      description: "Incidents occurring outside business hours (before 9 AM or after 5 PM) or on weekends. Timezone-aware based on this member's local time."
    },
    severity_weighted: {
      title: "Workload Intensity",
      description: "Measures workload stress by weighting incidents based on their severity level. Higher values indicate more stressful workload."
    }
  }

  // Calculate 7-day running average
  const calculate7DayRunningAverage = (scores: number[]) => {
    return scores.map((score, index) => {
      // For points with < 7 previous data points, use average up to that point (inclusive)
      const windowSize = Math.min(7, index + 1);
      const start = Math.max(0, index - windowSize + 1);
      const window = scores.slice(start, index + 1);
      const average = window.reduce((a, b) => a + b, 0) / window.length;
      return Math.round(average);
    });
  };

  useEffect(() => {
    const fetchDailyHealth = async () => {
      if (!memberData?.user_email || !analysisId) {
        return;
      }

      setLoading(true);

      try {
        const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const url = `${API_BASE}/analyses/${analysisId}/members/${encodeURIComponent(memberData.user_email)}/daily-health`;

        const response = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          const result = await response.json();
          if (result.status === 'success' && result.data?.daily_health) {
            setDailyHealthData(result.data.daily_health);
          }
        }
      } catch (err) {
        console.error('Error fetching user daily health:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDailyHealth();
  }, [memberData?.user_email, analysisId]);

  // Get the chart data with dynamic metric support
  const getChartData = () => {
    if (!dailyHealthData || dailyHealthData.length === 0) {
      return [];
    }

    const config = METRIC_CONFIG[selectedMetric];

    // Transform data using metric-specific transformer
    const chartData = dailyHealthData.map((day: any) => {
      const metricValue = config.transformer(day);

      return {
        date: new Date(day.date).toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric'
        }),
        originalDate: day.date,
        [config.dataKey]: metricValue,
        incidentCount: day.incident_count || 0,
        hasData: day.has_data || false
      };
    });

    // Calculate mean for the selected metric
    const values = chartData
      .filter((d: any) => d.hasData)
      .map((d: any) => d[config.dataKey]);

    const mean = values.length > 0
      ? values.reduce((a: number, b: number) => a + b, 0) / values.length
      : 0;

    // Add mean to each data point
    return chartData.map((d: any) => ({
      ...d,
      meanScore: Math.round(mean)
    }));
  };

  // Calculate statistics from daily health data
  const stats = useMemo(() => {
    const chartData = getChartData();
    const config = METRIC_CONFIG[selectedMetric];

    const values = chartData
      .filter((d: any) => d.hasData)
      .map((d: any) => d[config.dataKey]);

    if (values.length === 0) {
      return { mean: 0, min: 0, max: 0 };
    }

    const mean = values.reduce((a: number, b: number) => a + b, 0) / values.length;
    const min = Math.min(...values);
    const max = Math.max(...values);

    return { mean, min, max };
  }, [dailyHealthData, selectedMetric]);

  // Get chart mode from backend analysis data (default to 'normal')
  const chartMode = currentAnalysis?.analysis_data?.chart_mode || 'normal';

  // Get base chart data
  const chartData = getChartData();
  const hasData = chartData.length > 0;

  // Apply running average if mode is set (only for health_score)
  const processedChartData = (() => {
    if (chartMode === 'running_average' && chartData.length > 0 && selectedMetric === 'health_score') {
      const config = METRIC_CONFIG[selectedMetric];
      const scores = chartData.map(d => d[config.dataKey]);
      const averagedScores = calculate7DayRunningAverage(scores);
      return chartData.map((d, index) => ({
        ...d,
        [config.dataKey]: averagedScores[index]
      }));
    }
    return chartData;
  })();

  const config = METRIC_CONFIG[selectedMetric];
  const description = hasData
    ? `Over the last ${timeRange} days, average ${
        config.yAxisLabel.toLowerCase()
      } was ${Math.round(stats.mean)}${
        selectedMetric === 'health_score' ? ' points' : ''
      }.`
    : "No daily trend data available for this user";

  return (
    <TrendsCard
      title="User Trends"
      description={description}
      chartData={processedChartData}
      loading={loading}
      selectedMetric={selectedMetric}
      onMetricChange={setSelectedMetric}
      metricConfig={METRIC_CONFIG}
      metricDescriptions={METRIC_DESCRIPTIONS}
      timeRange={Number(timeRange)}
    />
  )
}
