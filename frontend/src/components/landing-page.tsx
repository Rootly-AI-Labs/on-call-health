"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Activity, Link2, Brain, Target, Github, Chrome, Shield, Users, TrendingUp, Loader2 } from "lucide-react"
import Link from "next/link"
import Image from "next/image"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
console.log('API_BASE:', API_BASE) // Debug log to verify the URL

export default function LandingPage() {
  const [isLoading, setIsLoading] = useState<'google' | 'github' | null>(null)

  const handleGoogleLogin = async () => {
    try {
      setIsLoading('google')
      // Pass the current origin to the backend
      const currentOrigin = window.location.origin
      const response = await fetch(`${API_BASE}/auth/google?redirect_origin=${encodeURIComponent(currentOrigin)}`)
      
      // Check if response is ok before parsing JSON
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Google auth API error:', response.status, errorText)
        throw new Error(`Authentication failed: ${response.status}`)
      }
      
      // Check content type to ensure it's JSON
      const contentType = response.headers.get('content-type')
      if (!contentType || !contentType.includes('application/json')) {
        const responseText = await response.text()
        console.error('Expected JSON but got:', contentType, responseText)
        throw new Error('Invalid response format from authentication server')
      }
      
      const data = await response.json()
      if (data.authorization_url) {
        window.location.href = data.authorization_url
      } else {
        console.error('No authorization URL in response:', data)
        throw new Error('Invalid authentication response')
      }
    } catch (error) {
      console.error('Google login error:', error)
      setIsLoading(null) // Reset loading state on error
    }
  }

  const handleGitHubLogin = async () => {
    try {
      setIsLoading('github')
      // Pass the current origin to the backend
      const currentOrigin = window.location.origin
      const response = await fetch(`${API_BASE}/auth/github?redirect_origin=${encodeURIComponent(currentOrigin)}`)
      const data = await response.json()
      if (data.authorization_url) {
        window.location.href = data.authorization_url
      }
    } catch (error) {
      console.error('GitHub login error:', error)
      setIsLoading(null) // Reset loading state on error
    }
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white">
        <div className="container mx-auto px-4 py-2">
          <div className="flex items-center">
            <div className="flex items-center">
              <span className="text-2xl font-bold text-slate-900">OnCall Burnout</span>
              <div className="ml-2 flex flex-col items-start -space-y-1">
                <span className="text-xs text-slate-400">powered by</span>
                <Image 
                  src="/images/rootly-ai-logo.png" 
                  alt="Rootly AI" 
                  width={160} 
                  height={64}
                  className="h-8 w-auto"
                />
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-20 lg:py-32 bg-gradient-to-b from-slate-50 to-white">
        <div className="container mx-auto px-4 text-center">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-slate-900 mb-6 leading-tight">
              Prevent Engineering Burnout Before It
              <span className="bg-gradient-to-r from-purple-600 to-purple-400 bg-clip-text text-transparent">
                {" "}
                Impacts Your Team
              </span>
            </h1>

            <p className="text-xl md:text-2xl text-slate-600 mb-12 max-w-3xl mx-auto leading-relaxed">
              Analyze incident response patterns to identify burnout risk and take action early
            </p>

            {/* OAuth Login Buttons */}
            <div id="login" className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-6">
              <Button
                size="lg"
                className="w-full sm:w-auto bg-slate-900 hover:bg-slate-800 text-white px-8 py-4 text-lg"
                onClick={handleGitHubLogin}
                disabled={isLoading === 'github'}
              >
                {isLoading === 'github' ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-3 animate-spin" />
                    Connecting to GitHub...
                  </>
                ) : (
                  <>
                    <Github className="w-5 h-5 mr-3" />
                    Continue with GitHub
                  </>
                )}
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="w-full sm:w-auto border-slate-300 px-8 py-4 text-lg hover:bg-slate-50 bg-transparent"
                onClick={handleGoogleLogin}
                disabled={isLoading === 'google'}
              >
                {isLoading === 'google' ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-3 animate-spin" />
                    Connecting to Google...
                  </>
                ) : (
                  <>
                    <Chrome className="w-5 h-5 mr-3" />
                    Continue with Google
                  </>
                )}
              </Button>
            </div>

          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="pt-8 pb-12 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">How It Works</h2>
            <p className="text-lg text-slate-600 max-w-3xl mx-auto">
              Based on scientifically validated burnout research methodology
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            <Card className="border-2 border-purple-200 bg-purple-25 hover:border-purple-300 transition-all duration-300 rounded-2xl">
              <CardContent className="p-8">
                <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm border border-purple-100">
                  <Link2 className="w-8 h-8 text-purple-600" />
                </div>
                <h3 className="text-xl font-semibold text-slate-900 mb-4 text-center">Multi-Source Data Collection</h3>
                <p className="text-slate-600 leading-relaxed text-center mb-4">
                  Connect your incident management, development, and communication tools
                </p>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                    <span className="text-slate-600">Incident data (Rootly/PagerDuty)</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                    <span className="text-slate-600">Code activity (GitHub)</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                    <span className="text-slate-600">Communication patterns (Slack)</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-2 border-purple-200 bg-purple-25 hover:border-purple-300 transition-all duration-300 rounded-2xl">
              <CardContent className="p-8">
                <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm border border-purple-100">
                  <Brain className="w-8 h-8 text-purple-600" />
                </div>
                <h3 className="text-xl font-semibold text-slate-900 mb-4 text-center">Three-Dimensional Analysis</h3>
                <p className="text-slate-600 leading-relaxed text-center mb-4">
                  Scientific burnout assessment across key psychological dimensions
                </p>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                    <span className="text-slate-600"><strong>Emotional Exhaustion</strong> (40%)</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                    <span className="text-slate-600"><strong>Depersonalization</strong> (30%)</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-slate-600"><strong>Personal Accomplishment</strong> (30%)</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-2 border-purple-200 bg-purple-25 hover:border-purple-300 transition-all duration-300 rounded-2xl">
              <CardContent className="p-8">
                <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm border border-purple-100">
                  <Target className="w-8 h-8 text-purple-600" />
                </div>
                <h3 className="text-xl font-semibold text-slate-900 mb-4 text-center">Risk-Based Recommendations</h3>
                <p className="text-slate-600 leading-relaxed text-center mb-4">
                  Get targeted interventions based on your team's specific risk profile
                </p>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-slate-600"><strong>Low Risk:</strong> Maintain balance</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                    <span className="text-slate-600"><strong>Medium Risk:</strong> Early intervention</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                    <span className="text-slate-600"><strong>High Risk:</strong> Immediate action</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Methodology highlight */}
          <div className="mt-12 text-center">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 max-w-4xl mx-auto">
              <p className="text-blue-800 text-sm leading-relaxed">
                <strong>Evidence-Based Approach:</strong> Our analysis combines workload pressure, after-hours activity, 
                response time patterns, and communication sentiment to provide a comprehensive burnout risk assessment. 
                The system adapts based on your available integrations to deliver the most accurate insights possible.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Value Proposition Section */}
      <section id="about" className="py-20 bg-gradient-to-r from-purple-50 to-purple-100">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-8">
              Built for engineering leaders who care about their team's well-being
            </h2>

            <p className="text-xl text-slate-600 mb-12 leading-relaxed">
              Make data-driven decisions about workload distribution and on-call rotations
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
              <div className="flex flex-col items-center">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                  <Shield className="w-6 h-6 text-purple-600" />
                </div>
                <h3 className="font-semibold text-slate-900 mb-2">Privacy First</h3>
                <p className="text-slate-600 text-sm">Your data stays secure with enterprise-grade encryption</p>
              </div>

              <div className="flex flex-col items-center">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                  <Users className="w-6 h-6 text-purple-600" />
                </div>
                <h3 className="font-semibold text-slate-900 mb-2">Team Focused</h3>
                <p className="text-slate-600 text-sm">Designed specifically for engineering team dynamics</p>
              </div>

              <div className="flex flex-col items-center">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                  <TrendingUp className="w-6 h-6 text-purple-600" />
                </div>
                <h3 className="font-semibold text-slate-900 mb-2">Actionable Data</h3>
                <p className="text-slate-600 text-sm">Clear insights you can act on immediately</p>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-300 py-12">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center mb-4 md:mb-0">
              <div className="flex items-center">
                <span className="text-2xl font-semibold text-white">OnCall Burnout</span>
                <div className="ml-2 flex flex-col items-start -space-y-1">
                  <span className="text-xs text-slate-500">powered by</span>
                  <Image 
                    src="/images/rootly-ai-logo.png" 
                    alt="Rootly AI" 
                    width={160} 
                    height={64}
                    className="h-8 w-auto opacity-80 brightness-0 invert"
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-6 text-sm">
              <a href="mailto:spencer.cheng@rootly.com" className="hover:text-white transition-colors">
                Support
              </a>
            </div>
          </div>

          <div className="border-t border-slate-800 mt-8 pt-8 text-center">
            <p className="text-slate-400">
              © {new Date().getFullYear()} OnCall Burnout by Rootly AI.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}