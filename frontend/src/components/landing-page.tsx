"use client"

import { useEffect, useRef, useState } from "react"
import localFont from "next/font/local"
import { Button } from "@/components/ui/button"
import { Github, Chrome, Loader2, Linkedin, Volume2, VolumeX } from "lucide-react"
import { siX } from "simple-icons"
import Image from "next/image"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

const ppMori = localFont({
  src: [
    { path: "../../public/fonts/PPMori/PPMori-Extralight.otf", weight: "200", style: "normal" },
    { path: "../../public/fonts/PPMori/PPMori-Book.otf", weight: "300", style: "normal" },
    { path: "../../public/fonts/PPMori/PPMori-Regular.otf", weight: "400", style: "normal" },
    { path: "../../public/fonts/PPMori/PPMori-RegularItalic.otf", weight: "400", style: "italic" },
    { path: "../../public/fonts/PPMori/PPMori-Semibold.otf", weight: "600", style: "normal" },
    { path: "../../public/fonts/PPMori/PPMori-ExtraBold.otf", weight: "800", style: "normal" },
  ],
})

export default function LandingPage() {
  const [isLoading, setIsLoading] = useState<"google" | "github" | null>(null)
  const [videoPaused, setVideoPaused] = useState(true)
  const [videoEnded, setVideoEnded] = useState(false)
  const [showContinueOverlay, setShowContinueOverlay] = useState(false)
  const [isMuted, setIsMuted] = useState(true)
  const [volume, setVolume] = useState(0.05)

  const mainRef = useRef<HTMLElement | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const heroSectionRef = useRef<HTMLElement | null>(null)

  const handleGoogleLogin = async () => {
    try {
      setIsLoading("google")
      const currentOrigin = window.location.origin
      const response = await fetch(
        `${API_BASE}/auth/google?redirect_origin=${encodeURIComponent(currentOrigin)}`
      )

      if (!response.ok) {
        const errorText = await response.text()
        console.error("Google auth API error:", response.status, errorText)
        throw new Error(`Authentication failed: ${response.status}`)
      }

      const contentType = response.headers.get("content-type")
      if (!contentType || !contentType.includes("application/json")) {
        const responseText = await response.text()
        console.error("Expected JSON but got:", contentType, responseText)
        throw new Error("Invalid response format from authentication server")
      }

      const data = await response.json()
      if (data.authorization_url) {
        window.location.href = data.authorization_url
      } else {
        console.error("No authorization URL in response:", data)
        throw new Error("Invalid authentication response")
      }
    } catch (error) {
      console.error("Google login error:", error)
      setIsLoading(null)
    }
  }

  const handleGitHubLogin = async () => {
    try {
      setIsLoading("github")
      const currentOrigin = window.location.origin
      const response = await fetch(
        `${API_BASE}/auth/github?redirect_origin=${encodeURIComponent(currentOrigin)}`
      )
      const data = await response.json()
      if (data.authorization_url) {
        window.location.href = data.authorization_url
      }
    } catch (error) {
      console.error("GitHub login error:", error)
      setIsLoading(null)
    }
  }

  const toggleVideoPlayback = () => {
    const video = videoRef.current
    if (!video) return

    if (video.paused || video.ended) {
      if (video.ended) video.currentTime = 0
      video.play().catch((error) => console.error("Video play error:", error))
    } else {
      video.pause()
    }
  }

  const handleVideoSurfaceClick = () => {
    const video = videoRef.current
    if (!video) return
    if (!video.paused && !video.ended) {
      video.pause()
    }
    setShowContinueOverlay(true)
  }

  const toggleVideoMute = () => {
    const video = videoRef.current
    if (!video) return

    const nextMuted = !video.muted
    video.muted = nextMuted
    if (!nextMuted) {
      const nextVolume = volume === 0 ? 0.05 : volume
      video.volume = nextVolume
      setVolume(nextVolume)
    }
    setIsMuted(nextMuted)
  }

  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    video.muted = isMuted
    video.volume = volume
  }, [isMuted, volume])

  useEffect(() => {
    const main = mainRef.current
    const heroSection = heroSectionRef.current
    if (!main || !heroSection) return

    const updateSnapMode = () => {
      const heroTop = heroSection.offsetTop
      const shouldSnap = main.scrollTop <= heroTop + 2
      const nextMode = shouldSnap ? "y mandatory" : "none"
      if (main.style.scrollSnapType !== nextMode) {
        main.style.scrollSnapType = nextMode
      }
    }

    updateSnapMode()
    main.addEventListener("scroll", updateSnapMode, { passive: true })
    window.addEventListener("resize", updateSnapMode)

    return () => {
      main.removeEventListener("scroll", updateSnapMode)
      window.removeEventListener("resize", updateSnapMode)
    }
  }, [])

  return (
    <main
      ref={mainRef}
      className={`${ppMori.className} h-screen overflow-y-auto overflow-x-hidden bg-white landing-snap-container`}
    >
      {/* SNAP SECTION 1: VIDEO (exactly one viewport tall) */}
      <section className="snap-start h-screen" id="get-started">
        <div className="h-full bg-[url(/images/landing/rootly-bg.avif)] bg-cover bg-center bg-no-repeat lg:bg-[size:210%] lg:bg-[position:-1200px_-300px]">
          <div className="h-full pt-0">
            <div className="h-full w-screen relative left-1/2 right-1/2 -ml-[50vw] -mr-[50vw]">
              <div className="relative h-full w-full overflow-hidden bg-transparent">
                {showContinueOverlay ? (
                  <button
                    type="button"
                    onClick={toggleVideoPlayback}
                    className="absolute inset-0 z-10 flex items-center justify-center bg-transparent"
                    aria-label="Continue video"
                  >
                    <span className="rounded-full bg-[#7b6db1]/60 px-7 py-2.5 text-lg font-semibold text-white backdrop-blur-sm transition">
                      Continue
                    </span>
                  </button>
                ) : null}

                <div className="absolute inset-x-0 top-0 z-30 flex items-center justify-between gap-3 px-4 pt-4 lg:px-8 lg:pt-6">
                  <div className="flex items-center min-w-0">
                    <div className="mr-4 flex flex-col items-start -space-y-1">
                      <a href="https://rootly.com" target="_blank" rel="noreferrer">
                        <Image
                          src="/images/rootly-ai-logo.png"
                          alt="Rootly AI"
                          width={321}
                          height={129}
                          className="w-[120px] lg:w-[160px]"
                        />
                      </a>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-sm leading-[1rem] lg:text-lg font-semibold text-slate-900">
                        On-Call Health
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation()
                        toggleVideoMute()
                      }}
                      className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/70 text-slate-900 shadow-sm transition hover:bg-white"
                      aria-label={isMuted ? "Unmute video" : "Mute video"}
                    >
                      {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <video
                  className="h-full w-full object-cover"
                  playsInline
                  preload="metadata"
                  autoPlay
                  muted
                  ref={videoRef}
                  onClick={handleVideoSurfaceClick}
                  onPlay={() => {
                    setVideoPaused(false)
                    setVideoEnded(false)
                    setShowContinueOverlay(false)
                  }}
                  onPause={() => setVideoPaused(true)}
                  onEnded={() => {
                    setVideoPaused(true)
                    setVideoEnded(true)
                    setShowContinueOverlay(true)
                  }}
                >
                  <source src="/videos/och-promo-v1.mp4" type="video/mp4" />
                </video>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SNAP SECTION 2: HERO CONTENT (starts right after video snap) */}
      <section ref={heroSectionRef} className="snap-start min-h-screen">
        <div className="relative bg-[url(/images/landing/rootly-bg.avif)] bg-cover bg-center bg-no-repeat lg:bg-[size:210%] lg:bg-[position:-1200px_-300px] pb-16 pt-14 lg:pt-20 lg:pb-20">
          <a
            href="https://github.com/Rootly-AI-Labs/On-Call-Health"
            target="_blank"
            rel="noreferrer"
            className="absolute right-6 top-6 z-20 rounded-2xl bg-[#7b6db1] px-4 py-2 text-xs font-semibold font-display text-[color:var(--text-text-primary,_#100F12)] hover:bg-[#6f62a5]"
          >
            GitHub
          </a>
          <div className="container mx-auto px-4">
            <div className="mt-20 mx-auto w-full max-w-4xl text-white">
              <div className="mx-auto max-w-3xl text-center">
                <div className="mb-8 flex items-center justify-center">
                  <span className="rounded-full border border-white/40 px-3 pt-1.5 pb-0.5 text-xs font-semibold uppercase tracking-[0.2em] text-white/90">
                    Open Source · Apache License 2.0
                  </span>
                </div>
                <h1 className="mb-8 text-4xl font-semibold tracking-tight leading-snug lg:text-6xl">
                  Catch overload before
                  <br /> it burns out your engineers.
                </h1>
                <p className="mt-4 mb-10 text-lg text-white/85 lg:text-xl">
                  An open source tool that looks for early warning signs of overload in your on-call engineers.
                </p>

                <div id="login" className="mt-8 flex flex-col sm:flex-row gap-5 items-center justify-center">
                  <Button
                    size="lg"
                    className="w-full rounded-3xl sm:w-auto bg-[#E4E5EB] hover:bg-[#d7d8de] text-[color:var(--color-blue-15,_#1E1A33)] px-8 py-7 text-lg font-display font-bold flex items-center justify-center"
                    onClick={handleGoogleLogin}
                    disabled={isLoading === "google"}
                  >
                    <span className="flex items-center justify-center gap-3 translate-y-[1.5px]">
                      {isLoading === "google" ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          Connecting to Google...
                        </>
                      ) : (
                        <>
                          <Chrome className="h-7 w-7 -translate-y-0.5" aria-hidden="true" />
                          Start with Google
                        </>
                      )}
                    </span>
                  </Button>

                  <Button
                    size="lg"
                    className="w-full rounded-3xl sm:w-auto bg-[#100F12] hover:bg-[#1b1a1e] text-[color:var(--text-text-contrast,_#FFFFFF)] px-8 py-7 text-lg font-display font-bold flex items-center justify-center"
                    onClick={handleGitHubLogin}
                    disabled={isLoading === "github"}
                  >
                    <span className="flex items-center justify-center gap-3 translate-y-[1.5px]">
                      {isLoading === "github" ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          Connecting to GitHub...
                        </>
                      ) : (
                        <>
                          <Github className="h-7 w-7 -translate-y-0.5" aria-hidden="true" />
                          Start with GitHub
                        </>
                      )}
                    </span>
                  </Button>
                </div>
                <div className="mx-auto mt-12 h-px w-16 bg-white/20" aria-hidden="true" />
                <p className="mt-5 text-sm tracking-wide text-white/80">
                  Built by engineers at Rootly.
                  <br className="hidden sm:block" />
                  Rootly&apos;s incident response platform powers teams at NVIDIA, Figma, Mistral AI, Replit, and more.
                </p>
              </div>

              <div className="pt-36">
                <Image
                  src="/images/landing/upstart-asset.png"
                  alt="Rootly customer story"
                  width={1200}
                  height={301}
                  className="w-full h-auto"
                  sizes="(min-width: 1024px) 896px, 90vw"
                  quality={100}
                  priority
                />
              </div>
            </div>
          </div>

          <div className="w-full mb-[-1px] absolute h-[120px] bottom-0 left-0 z-0 lg:h-[250px] bg-[url(/images/landing/rootly-bg-gradient.avif)] bg-contain bg-repeat-x pointer-events-none" />
        </div>
      </section>

      {/* How It Works Section */}
      <section className="pt-8 pb-12 bg-white lg:pt-8">
        <div className="container mx-auto px-4">
          <div className="text-center mb-4">
            <h2 className="text-4xl md:text-5xl font-semibold text-slate-900 mb-4">
              Sustainable work backed by data.
            </h2>
            <p className="text-lg text-slate-600 max-w-3xl mx-auto">Proof you can act on to justify change.</p>
            <Image
              src="/images/landing/integration-dashboard.png"
              alt="Integration dashboard overview"
              width={1200}
              height={661}
              className="w-[60%] h-auto mt-20 mb-20 mx-auto"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 w-[80%] mx-auto items-stretch">
            <div
              className="rounded-2xl border border-purple-100 px-7 pt-7 pb-2 h-full min-h-[300px]"
              style={{ background: "var(--surface-surface-bg-accent-shade, #F7F5FF)" }}
            >
              <h3 className="text-xl font-semibold text-slate-900 mb-6">Connect signals</h3>
              <p className="text-slate-600 leading-relaxed mb-0 mt-2">
                Start with Rootly or PagerDuty for incident data, add Linear for ticket workload, GitHub for after-hours
                signals, and Slack for communication patterns and context.
              </p>
            </div>

            <div
              className="rounded-2xl border border-purple-100 px-6 pt-6 pb-0 h-full min-h-[300px]"
              style={{ background: "var(--surface-surface-bg-accent-shade, #F7F5FF)" }}
            >
              <h3 className="text-xl font-semibold text-slate-900 mb-6">Collect sentiment</h3>
              <p className="text-slate-600 leading-relaxed mb-0 mt-2">
                Periodically send short surveys in Slack so responders can share how they're doing. Fast, low-friction,
                and designed to reduce stigma (not create it).
              </p>
            </div>

            <div
              className="rounded-2xl border border-purple-100 px-6 pt-6 pb-0 h-full min-h-[300px]"
              style={{ background: "var(--surface-surface-bg-accent-shade, #F7F5FF)" }}
            >
              <h3 className="text-xl font-semibold text-slate-900 mb-6">See who's at risk</h3>
              <p className="text-slate-600 leading-relaxed mb-0 mt-2">
                On-Call Health computes individual risk scores from ingested data:
                <span className="text-green-600 font-semibold"> 0-24</span> Maintain balance,
                <span className="text-yellow-600 font-semibold"> 25-49</span> Monitor risk,
                <span className="text-orange-600 font-semibold"> 50-74</span> Early intervention,
                <span className="text-red-600 font-semibold"> 75-100</span> Immediate action.
              </p>
            </div>

            <div
              className="rounded-2xl border border-purple-100 px-6 pt-6 pb-0 h-full min-h-[300px]"
              style={{ background: "var(--surface-surface-bg-accent-shade, #F7F5FF)" }}
            >
              <h3 className="text-xl font-semibold text-slate-900 mb-6">Act early with confidence</h3>
              <p className="text-slate-600 leading-relaxed mb-0 mt-2">
                AI analyzes what changed (and what’s driving it) so you can make better, informed decisions to protect
                your engineers before risk becomes burnout.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="mt-32">
        <div className="container mt-10">
          <div className="grid grid-cols-1 lg:grid-cols-2 items-center gap-12 w-[80%] mx-auto">
            <div className="py-10">
              <h2 className="text-3xl md:text-4xl text-slate-900 mb-4">Catch overload before it becomes burnout.</h2>
              <p className="mb-2 text-lg text-[#787685]">
                Spot trend shifts before burnout becomes reality—so you can intervene while fixes are still small:
                rebalance rotations, add automation, pause non-urgent work, or staff up.
              </p>
            </div>
            <div className="relative w-full aspect-[645/562]">
              <Image
                src="/images/landing/risk-factors.png"
                alt="Risk factors team card"
                fill
                sizes="(min-width: 1024px) 50vw, 100vw"
                className="object-contain"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 items-center gap-12 mt-20 mb-20 w-[80%] mx-auto">
            <div className="py-10 lg:order-last">
              <h2 className="text-3xl md:text-4xl text-slate-900 mb-4">Make on-call health measurable and fair.</h2>
              <p className="mb-2 text-lg text-[#787685]">
                On-Call Health uses team and individual-specific baselines to track trends over time, rather than
                relying on fixed thresholds or comparing people to each other.
              </p>
            </div>
            <div className="relative w-full aspect-[645/562]">
              <Image
                src="/images/landing/trends.png"
                alt="Team Risk Factors Trends"
                fill
                sizes="(min-width: 1024px) 50vw, 100vw"
                className="object-contain"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 items-center gap-12 mt-20 w-[80%] mx-auto">
            <div className="py-10">
              <h2 className="text-3xl md:text-4xl text-slate-900 mb-4">
                Align the team and act <br /> faster.
              </h2>
              <p className="mb-2 text-lg text-[#787685]">
                AI summaries help stakeholders quickly get up to speed on trends they may have missed, turning weekly
                incident reviews into conversations about not just systems, but also the people behind them.
              </p>
            </div>
            <div className="relative w-full aspect-[645/562]">
              <Image
                src="/images/landing/ai-views.png"
                alt="Screenshots of AI Team insights"
                fill
                sizes="(min-width: 1024px) 50vw, 100vw"
                className="object-contain"
              />
            </div>
          </div>

          <div className="mt-10 lg:mt-20 mb-0 w-screen relative left-1/2 right-1/2 -ml-[50vw] -mr-[50vw] bg-[url(/images/landing/cta-background.png)] bg-cover bg-[center_top] lg:bg-[center_top_-450px]">
            <div className="grid place-items-center px-6 py-16 lg:py-20 text-center">
              <h2 className="text-4xl md:text-5xl font-medium text-slate-900 mb-6">
                Detect who&apos;s at risk of burnout
                <br /> in your team today.
              </h2>
              <div className="flex flex-col justify-center sm:flex-row gap-4 items-center mb-6">
                <a
                  href="#get-started"
                  className="w-full inline-flex items-center justify-center rounded-2xl sm:w-auto bg-[#7a6db4] hover:bg-[#6b5fa8] text-white px-8 py-3 text-lg"
                >
                  Get started for free
                </a>
                <a
                  href="https://github.com/Rootly-AI-Labs/On-Call-Health"
                  target="_blank"
                  rel="noreferrer"
                  className="w-full inline-flex items-center justify-center rounded-2xl sm:w-auto bg-slate-900 hover:bg-slate-800 text-white px-8 py-3 text-lg"
                >
                  See project on GitHub
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer className="bg-[#0b0c10] text-white py-8 lg:py-12">
        <div className="container mx-auto px-4">
          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-8">
            <div>
              <a href="https://rootly.com" target="_blank" rel="noreferrer">
                <Image
                  src="/images/rootly-ai-logo-white.png"
                  alt="Rootly AI"
                  width={820}
                  height={328}
                  className="w-[420px] lg:w-[600px] brightness-0 invert"
                />
              </a>
              <div className="mt-0 text-3xl lg:text-4xl font-medium">On-Call Health</div>
              <div className="mt-8 text-sm text-slate-300">
                © Rootly {new Date().getFullYear()}. All rights reserved. Privacy policy · Terms of use · Cookie
                Settings
              </div>
            </div>

            <div className="flex items-center gap-3 mt-8">
              <a
                href="https://x.com/rootlyhq"
                target="_blank"
                rel="noreferrer"
                aria-label="Rootly on X"
                className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/20"
              >
                <div
                  className="h-4 w-4 text-white"
                  dangerouslySetInnerHTML={{
                    __html: siX.svg
                      .replace(
                        /<svg/,
                        '<svg fill="currentColor" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round" stroke-linecap="round"'
                      )
                      .replace(/fill="[^"]*"/g, 'fill="currentColor"'),
                  }}
                />
              </a>

              <a
                href="https://www.linkedin.com/company/rootlyhq"
                target="_blank"
                rel="noreferrer"
                aria-label="Rootly on LinkedIn"
                className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/20"
              >
                <Linkedin className="h-6 w-6 text-white" />
              </a>
            </div>
          </div>
        </div>
      </footer>

      <style jsx global>{`
        .landing-snap-container {
          scroll-snap-type: y mandatory;
          scroll-behavior: smooth;
          overscroll-behavior-y: contain;
        }

        .landing-snap-container > section {
          scroll-snap-stop: normal;
        }

        @media (prefers-reduced-motion: reduce) {
          .landing-snap-container {
            scroll-snap-type: none;
            scroll-behavior: auto;
          }
        }
      `}</style>
    </main>
  )
}

