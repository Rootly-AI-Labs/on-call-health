import { Inter } from 'next/font/google'
import Script from 'next/script'
import './globals.css'
import ErrorBoundary from '@/components/error-boundary'
import NewRelicProvider from '@/components/NewRelicProvider'
import ClientToaster from '@/components/ClientToaster'
import { GettingStartedProvider } from '@/contexts/GettingStartedContext'
import { GettingStartedDialog } from '@/components/GettingStartedDialog'
import { ChartModeProvider } from '@/contexts/ChartModeContext'
import { baseMetadata } from '@/lib/metadata'

const inter = Inter({ subsets: ['latin'] })

export const metadata = baseMetadata

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const gaMeasurementId = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID

  return (
    <html lang="en">
      <head>
        <style dangerouslySetInnerHTML={{__html: `
          *::selection,
          button::selection,
          [role="tab"]::selection,
          .text-white::selection,
          [data-state="active"]::selection,
          [data-state="checked"]::selection {
            background-color: #BFDBFE !important;
            color: #1E1E26 !important;
            -webkit-text-fill-color: #1E1E26 !important;
            --tw-text-opacity: 1 !important;
          }
          *::-moz-selection,
          button::-moz-selection,
          [role="tab"]::-moz-selection,
          .text-white::-moz-selection,
          [data-state="active"]::-moz-selection,
          [data-state="checked"]::-moz-selection {
            background-color: #BFDBFE !important;
            color: #1E1E26 !important;
          }
        `}} />
      </head>
      <body className={inter.className}>
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
