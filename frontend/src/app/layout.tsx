import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import ErrorBoundary from '@/components/error-boundary'
import { ToastProvider } from '@/hooks/use-toast-simple'
import { SimpleToastDisplay } from '@/components/simple-toast-display'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Rootly Burnout Detector',
  description: 'Prevent engineering burnout before it impacts your team',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ToastProvider>
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
          <SimpleToastDisplay />
        </ToastProvider>
      </body>
    </html>
  )
}