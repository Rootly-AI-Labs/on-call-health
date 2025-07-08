"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Activity,
  CheckCircle,
  Shield,
  LogOut,
  ChevronRight,
  Github,
  Chrome,
} from "lucide-react"
import { useRouter } from "next/navigation"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface User {
  name: string
  email: string
  avatar: string
  provider: string
}

export default function AuthSuccessPage() {
  const [user, setUser] = useState<User | null>(null)
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
        }
      }
    }
    
    fetchUserData()
  }, [])

  const handleContinue = () => {
    router.push('/integrations')
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
                Authentication Success
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
              <DropdownMenuContent className="w-40" align="end" forceMount>
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
        <div className="max-w-2xl mx-auto text-center">
          {/* Success Icon */}
          <div className="w-20 h-20 bg-white border-2 border-purple-200 rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm">
            <CheckCircle className="w-10 h-10 text-purple-600" />
          </div>

          {/* Welcome Message */}
          <h1 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">
            Welcome, {user.name.split(' ')[0]}!
          </h1>

          <div className="flex items-center justify-center space-x-2 mb-6">
            <p className="text-lg text-slate-600">
              You're successfully logged in with
            </p>
            <Badge variant="outline" className="flex items-center space-x-1 border-purple-200 text-purple-700">
              {getProviderIcon(user.provider)}
              <span>{user.provider}</span>
            </Badge>
          </div>

          {/* Security Info */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-8">
            <div className="flex items-start space-x-3 text-left">
              <Shield className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-blue-800">
                <p className="font-semibold mb-1 text-left">Your data is secure</p>
                <p className="text-left">We only analyze incident patterns to identify burnout risk. Your data is encrypted and never shared.</p>
              </div>
            </div>
          </div>

          {/* Continue Button */}
          <div className="space-y-4">
            <Button
              size="lg"
              className="w-full sm:w-auto bg-gradient-to-r from-purple-600 to-fuchsia-500 hover:from-purple-700 hover:to-fuchsia-600 text-white px-8 py-4 text-lg font-semibold shadow-lg hover:shadow-xl transition-all duration-200"
              onClick={handleContinue}
            >
              Continue to Integrations
              <ChevronRight className="w-5 h-5 ml-2" />
            </Button>
            
            <p className="text-sm text-slate-500">
              Connect your incident management platform to get started
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}