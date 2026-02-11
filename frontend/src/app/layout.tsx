import { Inter } from 'next/font/google'
import Script from 'next/script'
import './globals.css'
import ErrorBoundary from '@/components/error-boundary'
import NewRelicProvider from '@/components/NewRelicProvider'
import ClientToaster from '@/components/ClientToaster'
import { GettingStartedProvider } from '@/contexts/GettingStartedContext'
import { GettingStartedDialog } from '@/components/GettingStartedDialog'
import { ChartModeProvider } from '@/contexts/ChartModeContext'
import { baseMetadata, baseViewport } from '@/lib/metadata'
import AuthInterceptor from '@/components/AuthInterceptor'

const inter = Inter({ subsets: ['latin'] })

export const metadata = baseMetadata
export const viewport = baseViewport

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const gaMeasurementId = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Preload critical background images for landing page */}
        <link rel="preload" as="image" href="/images/landing/rootly-bg.avif" />
        <link rel="preload" as="image" href="/images/landing/rootly-bg-gradient.avif" />
      </head>
      <body className={inter.className} suppressHydrationWarning>
        {gaMeasurementId && (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${gaMeasurementId}`}
              strategy="afterInteractive"
            />
            <Script
              id="ga-script"
              strategy="afterInteractive"
              dangerouslySetInnerHTML={{
                __html: `
                  window.dataLayer = window.dataLayer || [];
                  function gtag(){dataLayer.push(arguments);}
                  gtag('js', new Date());
                  gtag('config', '${gaMeasurementId}');
                `,
              }}
            />
          </>
        )}
        <NewRelicProvider>
          <GettingStartedProvider>
            <ChartModeProvider>
              <AuthInterceptor />
              <ErrorBoundary>
                {children}
              </ErrorBoundary>
              <GettingStartedDialog />
              <ClientToaster />
            </ChartModeProvider>
          </GettingStartedProvider>
        </NewRelicProvider>
      </body>
    </html>
  )
}
