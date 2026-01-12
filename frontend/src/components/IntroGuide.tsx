"use client"

import { X, ChevronRight, ChevronLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import Image from "next/image"

interface IntroGuideProps {
  isOpen: boolean
  currentStep: number
  onNext: () => void
  onPrev: () => void
  onClose: () => void
}

function IntroGuide({ isOpen, currentStep, onNext, onPrev, onClose }: IntroGuideProps) {
  if (!isOpen) return null

  const steps = [
    {
      title: "Welcome to On-Call Health",
      description: "Detect early signs of overwork in your on-call team before it leads to burnout.",
      details:
        "Connects to Rootly, PagerDuty, GitHub, Slack, Linear, and Jira to compute a risk level.",
      image: "/images/integrations-logos.png",
    },
    {
      title: "Run an Analysis",
      description: "Choose your data sources, team members, and time range to analyze.",
      details: "Powered by Anthropic and OpenAI for AI-generated insights.",
      highlight: "mock-data-demo",
      image: "/images/mock-data-dashboard.png",
    },
    {
      title: "Explore Team-Wide Metrics",
      description: "Track risk levels, incident counts, after-hours activity, and workload trends across your team.",
      details: "",
      image: "/images/team-trends-dashboard.png",
    },
    {
      title: "Dive Into Responder-Specific Data",
      description: "Drill down into individual metrics to understand who needs support and why.",
      details: "",
      image: "/images/responder-detail-modal.png",
    },
    {
      title: "Let AI Do the Analysis Work",
      description: "Get AI-generated summaries to quickly prep for incident reviews or spot trends you might have missed.",
      details: "",
      image: "/images/ai-team-insights.png",
    },
  ]

  const step = steps[currentStep]

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white dark:bg-slate-950 rounded-lg shadow-xl max-w-4xl w-full border border-slate-200 dark:border-slate-800 max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="flex items-start justify-between p-6 border-b border-slate-200 dark:border-slate-800 sticky top-0 bg-white dark:bg-slate-950 z-10">
            <div className="flex items-center gap-3">
              <div>
                <h2 className="text-2xl font-semibold text-slate-900 dark:text-white">{step.title}</h2>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                  Step {currentStep + 1} of {steps.length}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md transition-colors"
            >
              <X className="w-5 h-5 text-slate-600 dark:text-slate-400" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            <p className="text-lg text-slate-700 dark:text-slate-300 mb-3">{step.description}</p>
            {step.details && (
              <p className="text-base text-slate-600 dark:text-slate-400 leading-relaxed mb-4">{step.details}</p>
            )}

            {step.image && (
              <div className="mt-6 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden bg-slate-50 dark:bg-slate-900/30">
                <div className="relative w-full">
                  <Image
                    src={step.image}
                    alt={step.title}
                    width={1200}
                    height={675}
                    className="w-full h-auto"
                    priority
                    quality={100}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Progress dots */}
          <div className="flex justify-center gap-2 px-6 py-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/30">
            {steps.map((_, index) => (
              <div
                key={index}
                className={`h-2 rounded-full transition-all ${
                  index === currentStep ? "w-6 bg-purple-600 dark:bg-purple-500" : "w-2 bg-slate-300 dark:bg-slate-600"
                }`}
              />
            ))}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between p-6 gap-3 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-200 dark:border-slate-800">
            <button
              onClick={onClose}
              className="text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors"
            >
              Skip
            </button>

            <div className="flex gap-3">
              <Button variant="outline" onClick={onPrev} disabled={currentStep === 0} className="gap-2 bg-transparent">
                <ChevronLeft className="w-4 h-4" />
                Previous
              </Button>
              <Button
                onClick={onNext}
                className="gap-2 bg-purple-600 hover:bg-purple-700 dark:bg-purple-600 dark:hover:bg-purple-700"
              >
                {currentStep === steps.length - 1 ? "Finish" : "Next"}
                {currentStep < steps.length - 1 && <ChevronRight className="w-4 h-4" />}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

export default IntroGuide
