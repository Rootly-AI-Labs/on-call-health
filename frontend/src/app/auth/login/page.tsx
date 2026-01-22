"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import Image from "next/image"

export default function LoginPage() {
  const router = useRouter()

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-50 to-blue-50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex flex-col items-center -space-y-0.5 mb-4">
            <div className="flex items-center gap-1.5">
              <span className="text-2xl font-normal text-black">On-Call Health</span>
              <Image
                src="/images/on-call-health-logo.svg"
                alt="On-Call Health"
                width={32}
                height={32}
                className="w-8 h-8"
              />
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-black/70 font-light">Powered by</span>
              <Image
                src="/images/rootly-ai-logo.png"
                alt="Rootly"
                width={321}
                height={129}
                className="w-[60px]"
              />
            </div>
          </div>
          <CardTitle className="text-2xl">Authentication Required</CardTitle>
          <CardDescription className="text-base mt-2">
            You need to sign in to access this page
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Button
            size="lg"
            onClick={() => router.push("/")}
            className="w-full bg-purple-700 hover:bg-purple-800 text-white"
          >
            Go to Sign In
          </Button>
          <p className="text-sm text-center text-neutral-500">
            Sign in with Google or GitHub to continue
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
