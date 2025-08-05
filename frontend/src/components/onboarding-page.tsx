"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Progress } from "@/components/ui/progress"
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
  Link2,
  Shield,
  LogOut,
  Settings,
  User,
  ChevronRight,
  Github,
  Chrome,
} from "lucide-react"
import Link from "next/link"
import { useRouter } from "next/navigation"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface User {
  name: string
  email: string
  avatar: string
  provider: string
}

export default function OnboardingPage() {
  const [user, setUser] = useState<User | null>(null)
  const router = useRouter()

  useEffect(() => {
    const fetchUserData = async () => {
      // Get JWT token from URL params
      const urlParams = new URLSearchParams(window.location.search)
      const token = urlParams.get('token') || localStorage.getItem('auth_token')
      
      if (token) {
        try {
          // Store token for future API calls
          localStorage.setItem('auth_token', token)
          
          // Fetch user data from backend using the token
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
            
            // Store user data in localStorage for persistence
            localStorage.setItem('user_name', userData.name || '')
            localStorage.setItem('user_email', userData.email || '')
            localStorage.setItem('user_avatar', userData.avatar || '')
            localStorage.setItem('user_provider', userData.provider || '')
            
            // Clean up URL params
            window.history.replaceState({}, document.title, window.location.pathname)
          } else {
            throw new Error('Failed to fetch user data')
          }
        } catch (error) {
          console.error('Error fetching user data:', error)
          
          // Fallback to localStorage data
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
          } else {
            // Ultimate fallback
            setUser({
              name: "User",
              email: "user@example.com",
              avatar: "/placeholder.svg?height=40&width=40",
              provider: "Google"
            })
          }
        }
      } else {
        // No token available, use cached data or fallback
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
        } else {
          setUser({
            name: "User",
            email: "user@example.com",
            avatar: "/placeholder.svg?height=40&width=40",
            provider: "Google"
          })
        }
      }
    }
    
    fetchUserData()
  }, [])

  const handleSetupIntegrations = () => {
    // Direct navigation to integrations setup
    router.push('/integrations')
  }

  const getProviderIcon = (provider: string) => {
    return provider === "GitHub" ? <Github className="w-4 h-4" /> : <Chrome className="w-4 h-4" />
  }

  if (!user) {
    return <div className="min-h-screen bg-white flex items-center justify-center">Loading...</div>
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-purple-100 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-600 to-fuchsia-500 rounded-lg flex items-center justify-center shadow-lg">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold text-slate-900">Rootly Burnout Detector</span>
              <Badge variant="secondary" className="ml-2 text-xs bg-purple-100 text-purple-700">
                Setup
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
                <DropdownMenuItem>
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
        <div className="max-w-2xl mx-auto">
          {/* Welcome Section */}
          <div className="text-center mb-12">
            <div className="w-20 h-20 bg-white border-2 border-purple-200 rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm">
              <CheckCircle className="w-10 h-10 text-purple-600" />
            </div>

            <h1 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">Welcome to Rootly Burnout Detector</h1>

            <div className="flex items-center justify-center space-x-2 mb-4">
              <p className="text-lg text-slate-600">
                Hi <span className="font-semibold text-slate-900">{user.name}</span>, you're successfully logged in
                with
              </p>
              <Badge variant="outline" className="flex items-center space-x-1 border-purple-200 text-purple-700">
                {getProviderIcon(user.provider)}
                <span>{user.provider}</span>
              </Badge>
            </div>

            <p className="text-slate-600 text-lg">Let's connect your tools and start protecting your team's wellbeing</p>
          </div>

          {/* Progress Section */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-slate-700">Step 1 of 2: Connect Your Platform</span>
              <span className="text-sm text-slate-500">50% complete</span>
            </div>
            <Progress value={50} className="h-2 bg-purple-100">
              <div className="h-full bg-gradient-to-r from-purple-600 to-fuchsia-500 rounded-full transition-all duration-300" />
            </Progress>
          </div>

          {/* Information Card */}
          <Card className="border-2 border-purple-200 bg-white/70 backdrop-blur-sm shadow-lg mb-8">
            <CardContent className="p-8">
              <div className="flex items-start space-x-4">
                <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-fuchsia-500 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Link2 className="w-6 h-6 text-white" />
                </div>
                <div className="flex-1">
                  <h2 className="text-xl font-semibold text-slate-900 mb-3">Connect Your On-Call Platform</h2>
                  <p className="text-slate-600 mb-4 leading-relaxed">
                    To analyze your team's burnout patterns, we need access to your incident data from Rootly, PagerDuty, or other platforms. 
                    This helps us identify workload distribution, response patterns, and after-hours activity.
                  </p>
                  <div className="flex items-center space-x-2 text-sm text-slate-500">
                    <Shield className="w-4 h-4 text-purple-600" />
                    <span>Your data is processed securely and never shared with third parties</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Call to Action */}
          <div className="text-center space-y-4">
            <Button
              size="lg"
              className="w-full sm:w-auto bg-gradient-to-r from-purple-600 to-fuchsia-500 hover:from-purple-700 hover:to-fuchsia-600 text-white px-8 py-4 text-lg font-semibold shadow-lg hover:shadow-xl transition-all duration-200"
              onClick={handleSetupIntegrations}
            >
              Choose Your Platform
              <ChevronRight className="w-5 h-5 ml-2" />
            </Button>

          </div>

          {/* Next Steps Preview */}
          <div className="mt-12 p-6 bg-white/50 rounded-lg border border-purple-100">
            <h3 className="font-semibold text-slate-900 mb-2">What's next?</h3>
            <p className="text-sm text-slate-600 mb-3">
              After connecting your platform, we'll analyze your incident data and show you:
            </p>
            <ul className="text-sm text-slate-600 space-y-1">
              <li className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 bg-purple-500 rounded-full" />
                <span>Team burnout risk scores</span>
              </li>
              <li className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 bg-purple-500 rounded-full" />
                <span>Workload distribution patterns</span>
              </li>
              <li className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 bg-purple-500 rounded-full" />
                <span>Actionable recommendations</span>
              </li>
            </ul>
          </div>
        </div>
      </main>
    </div>
  )
}