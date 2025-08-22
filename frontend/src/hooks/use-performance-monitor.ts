import { useCallback, useEffect, useRef } from 'react'

interface PerformanceMetric {
  name: string
  startTime: number
  endTime?: number
  duration?: number
}

interface PerformanceData {
  pageLoadTime: number
  cacheHitTime: number
  apiCallTime: number
  renderTime: number
  totalApiCalls: number
  cacheHitRate: number
}

export function usePerformanceMonitor() {
  const metricsRef = useRef<PerformanceMetric[]>([])
  const performanceDataRef = useRef<PerformanceData>({
    pageLoadTime: 0,
    cacheHitTime: 0,
    apiCallTime: 0,
    renderTime: 0,
    totalApiCalls: 0,
    cacheHitRate: 0
  })

  // Start timing a metric
  const startTiming = useCallback((name: string) => {
    const metric: PerformanceMetric = {
      name,
      startTime: performance.now()
    }
    metricsRef.current.push(metric)
    console.log(`🚀 PERF: Started timing ${name}`)
    return name
  }, [])

  // End timing a metric
  const endTiming = useCallback((name: string) => {
    const endTime = performance.now()
    const metric = metricsRef.current.find(m => m.name === name && !m.endTime)
    
    if (metric) {
      metric.endTime = endTime
      metric.duration = endTime - metric.startTime
      console.log(`✅ PERF: ${name} took ${metric.duration.toFixed(2)}ms`)
      
      // Update performance data
      switch (name) {
        case 'page_load':
          performanceDataRef.current.pageLoadTime = metric.duration
          break
        case 'cache_load':
          performanceDataRef.current.cacheHitTime = metric.duration
          break
        case 'api_call':
          performanceDataRef.current.apiCallTime += metric.duration
          performanceDataRef.current.totalApiCalls++
          break
        case 'render':
          performanceDataRef.current.renderTime = metric.duration
          break
      }
    }
  }, [])

  // Track cache performance
  const trackCacheHit = useCallback(() => {
    const current = performanceDataRef.current
    current.cacheHitRate = (current.cacheHitRate * current.totalApiCalls + 1) / (current.totalApiCalls + 1)
    console.log(`📊 PERF: Cache hit rate: ${(current.cacheHitRate * 100).toFixed(1)}%`)
  }, [])

  // Get performance summary
  const getPerformanceSummary = useCallback(() => {
    const data = performanceDataRef.current
    const completedMetrics = metricsRef.current.filter(m => m.duration)
    
    return {
      ...data,
      metrics: completedMetrics,
      summary: {
        totalTime: data.pageLoadTime + data.renderTime,
        cacheEfficiency: data.cacheHitTime < 100 ? 'excellent' : data.cacheHitTime < 500 ? 'good' : 'needs_improvement',
        apiEfficiency: data.totalApiCalls < 5 ? 'excellent' : data.totalApiCalls < 10 ? 'good' : 'needs_improvement'
      }
    }
  }, [])

  // Log performance summary (development only)
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      const timer = setTimeout(() => {
        const summary = getPerformanceSummary()
        console.group('🎯 PERFORMANCE SUMMARY')
        console.log('Page Load:', `${summary.pageLoadTime.toFixed(2)}ms`)
        console.log('Cache Load:', `${summary.cacheHitTime.toFixed(2)}ms`)
        console.log('Total API Time:', `${summary.apiCallTime.toFixed(2)}ms`)
        console.log('Render Time:', `${summary.renderTime.toFixed(2)}ms`)
        console.log('Total API Calls:', summary.totalApiCalls)
        console.log('Cache Hit Rate:', `${(summary.cacheHitRate * 100).toFixed(1)}%`)
        console.log('Overall Efficiency:', summary.summary.cacheEfficiency)
        console.groupEnd()
      }, 5000) // Log summary after 5 seconds

      return () => clearTimeout(timer)
    }
  }, [getPerformanceSummary])

  return {
    startTiming,
    endTiming,
    trackCacheHit,
    getPerformanceSummary
  }
}