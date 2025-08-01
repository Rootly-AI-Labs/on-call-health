"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Activity,
  CheckCircle,
  Shield,
  LogOut,
  Settings,
  User,
  ChevronRight,
  Github,
  Chrome,
  AlertTriangle,
  Zap,
  Users,
  Clock,
  TrendingUp,
} from "lucide-react"
import Image from "next/image"
import { useRouter } from "next/navigation"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface User {
  name: string
  email: string
  avatar: string
  provider: string
}

export default function PlatformSelectionPage() {
  const [user, setUser] = useState<User | null>(null)
  const [selectedPlatform, setSelectedPlatform] = useState<"rootly" | "pagerduty" | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()

  useEffect(() => {
    const fetchUserData = async () => {
      const urlParams = new URLSearchParams(window.location.search)
      const token = urlParams.get('token') || localStorage.getItem('auth_token')
      
      if (token) {
        try {
          localStorage.setItem('auth_token', token)
          
          const response = await fetch(`${API_BASE}/auth/me`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
          
          if (response.ok) {
            const userData = await response.json()
            setUser({
              name: userData.name || 'User',
              email: userData.email || 'user@example.com',
              avatar: userData.avatar || "/placeholder.svg?height=40&width=40",
              provider: userData.provider || 'Google'
            })
            
            localStorage.setItem('user_name', userData.name || '')
            localStorage.setItem('user_email', userData.email || '')
            localStorage.setItem('user_avatar', userData.avatar || '')
            localStorage.setItem('user_provider', userData.provider || '')
            
            window.history.replaceState({}, document.title, window.location.pathname)
          }
        } catch (error) {
          console.error('Error fetching user data:', error)
          
          const cachedName = localStorage.getItem('user_name')
          const cachedEmail = localStorage.getItem('user_email')
          const cachedProvider = localStorage.getItem('user_provider')
          
          if (cachedName && cachedEmail && cachedProvider) {
            setUser({
              name: cachedName,
              email: cachedEmail,
              avatar: localStorage.getItem('user_avatar') || "/placeholder.svg?height=40&width=40",
              provider: cachedProvider
            })
          }
        }
      }
    }
    
    fetchUserData()
  }, [])

  const handlePlatformSelect = (platform: "rootly" | "pagerduty") => {
    setSelectedPlatform(platform)
  }

  const handleContinue = async () => {
    if (!selectedPlatform) return
    
    setIsLoading(true)
    
    // Store platform preference
    localStorage.setItem('selected_platform', selectedPlatform)
    
    // Check if user already has integration for this platform
    try {
      const response = await fetch(`${API_BASE}/integrations`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        const hasIntegration = data.integrations?.some((i: any) => 
          i.platform === selectedPlatform && i.is_active
        )
        
        if (hasIntegration) {
          // User already has integration, go to dashboard
          router.push('/dashboard')
        } else {
          // Go to platform-specific setup
          if (selectedPlatform === 'rootly') {
            router.push('/integrations')
          } else {
            router.push('/integrations')
          }
        }
      } else {
        // If check fails, go to setup anyway
        if (selectedPlatform === 'rootly') {
          router.push('/integrations')
        } else {
          router.push('/setup/pagerduty')
        }
      }
    } catch (error) {
      console.error('Error checking integrations:', error)
      // Go to setup on error
      if (selectedPlatform === 'rootly') {
        router.push('/integrations')
      } else {
        router.push('/setup/pagerduty')
      }
    }
    
    setIsLoading(false)
  }

  const getProviderIcon = (provider: string) => {
    return provider === "GitHub" ? <Github className="w-4 h-4" /> : <Chrome className="w-4 h-4" />
  }

  if (!user) {
    return <div className="min-h-screen bg-white flex items-center justify-center">Loading...</div>
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-fuchsia-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-purple-100 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-600 to-fuchsia-500 rounded-lg flex items-center justify-center shadow-lg">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold text-slate-900">Burnout Detector</span>
              <Badge variant="secondary" className="ml-2 text-xs bg-purple-100 text-purple-700">
                Platform Selection
              </Badge>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="flex items-center space-x-2 hover:bg-purple-50">
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={user.avatar || "/placeholder.svg"} alt={user.name} />
                    <AvatarFallback className="bg-purple-100 text-purple-700">
                      {user.name
                        .split(" ")
                        .map((n) => n[0])
                        .join("")}
                    </AvatarFallback>
                  </Avatar>
                  <div className="text-left hidden sm:block">
                    <p className="text-sm font-medium text-slate-900">{user.name}</p>
                    <p className="text-xs text-slate-500">{user.email}</p>
                  </div>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-56" align="end" forceMount>
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">{user.name}</p>
                    <p className="text-xs leading-none text-muted-foreground">{user.email}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem>
                  <User className="mr-2 h-4 w-4" />
                  <span>Profile</span>
                </DropdownMenuItem>
                <DropdownMenuItem>
                  <Settings className="mr-2 h-4 w-4" />
                  <span>Settings</span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => {
                  localStorage.clear()
                  router.push('/')
                }}>
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Log out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto">
          {/* Welcome Section */}
          <div className="text-center mb-12">
            <div className="w-20 h-20 bg-white border-2 border-purple-200 rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm">
              <CheckCircle className="w-10 h-10 text-purple-600" />
            </div>

            <h1 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">
              Welcome, {user.name.split(' ')[0]}!
            </h1>

            <p className="text-lg text-slate-600 mb-2">
              Let&apos;s analyze your team&apos;s burnout risk
            </p>
            
            <p className="text-slate-600">
              Which incident management platform does your team use?
            </p>
          </div>

          {/* Platform Selection Cards */}
          <div className="grid md:grid-cols-2 gap-8 mb-8 max-w-2xl mx-auto">
            {/* Rootly Card */}
            <Card 
              className={`border-2 transition-all cursor-pointer hover:shadow-lg ${
                selectedPlatform === 'rootly' 
                  ? 'border-purple-500 shadow-lg bg-purple-50' 
                  : 'border-gray-200 hover:border-purple-300'
              } p-8 flex items-center justify-center relative h-32`}
              onClick={() => handlePlatformSelect('rootly')}
            >
              {selectedPlatform === 'rootly' && (
                <CheckCircle className="w-6 h-6 text-purple-600 absolute top-4 right-4" />
              )}
              <Image
                src="/images/rootly-logo-branded.png"
                alt="Rootly"
                width={220}
                height={50}
                className="h-12 w-auto object-contain"
              />
            </Card>

            {/* PagerDuty Card */}
            <Card 
              className={`border-2 transition-all cursor-pointer hover:shadow-lg ${
                selectedPlatform === 'pagerduty' 
                  ? 'border-green-500 shadow-lg bg-green-50' 
                  : 'border-gray-200 hover:border-green-300'
              } p-8 flex items-center justify-center relative h-32`}
              onClick={() => handlePlatformSelect('pagerduty')}
            >
              {selectedPlatform === 'pagerduty' && (
                <CheckCircle className="w-6 h-6 text-green-600 absolute top-4 right-4" />
              )}
              <div className="flex items-center space-x-2">
                <div className="w-10 h-10 bg-green-600 rounded flex items-center justify-center">
                  <span className="text-white font-bold text-base">PD</span>
                </div>
                <span className="text-2xl font-bold text-slate-900">PagerDuty</span>
              </div>
            </Card>
          </div>

          {/* Info Box */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-8">
            <div className="flex items-start space-x-3">
              <Shield className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-blue-800">
                <p className="font-semibold mb-1">Your data is secure</p>
                <p>We only analyze incident patterns to identify burnout risk. Your data is encrypted and never shared.</p>
              </div>
            </div>
          </div>

          {/* Continue Button */}
          <div className="text-center">
            <Button
              size="lg"
              className={`px-8 py-4 text-lg font-semibold shadow-lg transition-all duration-200 ${
                selectedPlatform 
                  ? 'bg-gradient-to-r from-purple-600 to-fuchsia-500 hover:from-purple-700 hover:to-fuchsia-600 text-white hover:shadow-xl' 
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
              onClick={handleContinue}
              disabled={!selectedPlatform || isLoading}
            >
              {isLoading ? (
                "Loading..."
              ) : selectedPlatform ? (
                <>
                  Continue with {selectedPlatform === 'rootly' ? 'Rootly' : 'PagerDuty'}
                  <ChevronRight className="w-5 h-5 ml-2" />
                </>
              ) : (
                <>
                  Select a platform to continue
                  <ChevronRight className="w-5 h-5 ml-2" />
                </>
              )}
            </Button>
            
            {!selectedPlatform && (
              <p className="text-sm text-slate-500 mt-3">
                Please select your incident management platform to continue
              </p>
            )}
          </div>

          {/* Future Integrations */}
          <div className="mt-12 text-center">
            <p className="text-sm text-slate-500 mb-3">More integrations coming soon:</p>
            <div className="flex items-center justify-center space-x-6">
              <div className="flex items-center space-x-2 text-slate-400">
                <Github className="w-5 h-5" />
                <span className="text-sm">GitHub</span>
              </div>
              <div className="flex items-center space-x-2 text-slate-400">
                <div className="w-5 h-5 bg-slate-400 rounded flex items-center justify-center">
                  <span className="text-white text-xs font-bold">S</span>
                </div>
                <span className="text-sm">Slack</span>
              </div>
              <div className="flex items-center space-x-2 text-slate-400">
                <div className="w-5 h-5 bg-slate-400 rounded flex items-center justify-center">
                  <span className="text-white text-xs font-bold">J</span>
                </div>
                <span className="text-sm">Jira</span>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}