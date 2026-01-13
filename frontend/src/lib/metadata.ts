import type { Metadata } from 'next'

/**
 * Central configuration for all site metadata
 * Used for SEO, social sharing (Open Graph), and browser display
 */

export const SITE_CONFIG = {
  name: 'Catch overload before it burns out your engineers.',
  shortName: 'On-Call Health',
  description: 'An open source tool that looks for early warning signs of overload in your on-call engineers.',
  url: process.env.NEXT_PUBLIC_SITE_URL || 'https://www.oncallhealth.ai',
  ogImage: '/images/landing/landing_page_preview.png',
  favicon: '/images/favicon.png',
  twitterHandle: '@rootlyhq',
} as const

/**
 * Base metadata template used as default for all pages
 */
export const baseMetadata: Metadata = {
  title: SITE_CONFIG.name,
  description: SITE_CONFIG.description,
  icons: {
    icon: SITE_CONFIG.favicon,
    shortcut: SITE_CONFIG.favicon,
    apple: SITE_CONFIG.favicon,
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: SITE_CONFIG.url,
    siteName: SITE_CONFIG.name,
    title: SITE_CONFIG.name,
    description: SITE_CONFIG.description,
    images: [
      {
        url: `${SITE_CONFIG.url}${SITE_CONFIG.ogImage}`,
        width: 1200,
        height: 630,
        alt: SITE_CONFIG.name,
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: SITE_CONFIG.name,
    description: SITE_CONFIG.description,
    images: [`${SITE_CONFIG.url}${SITE_CONFIG.ogImage}`],
    creator: SITE_CONFIG.twitterHandle,
  },
}

/**
 * Generate metadata for specific pages
 * @param title - Page title
 * @param description - Page description
 * @param ogImage - Optional custom OG image URL (relative path)
 * @returns Metadata object
 */
export function generatePageMetadata(
  title: string,
  description: string,
  ogImage?: string
): Metadata {
  const imageUrl = ogImage
    ? `${SITE_CONFIG.url}${ogImage}`
    : `${SITE_CONFIG.url}${SITE_CONFIG.ogImage}`

  return {
    title,
    description,
    openGraph: {
      ...baseMetadata.openGraph,
      title,
      description,
      images: [
        {
          url: imageUrl,
          width: 1200,
          height: 630,
          alt: title,
        },
      ],
    },
    twitter: {
      ...baseMetadata.twitter,
      title,
      description,
      images: [imageUrl],
    },
  }
}

/**
 * Metadata for landing/home page
 */
export const landingPageMetadata = generatePageMetadata(
  'On-Call Health',
  'Catch overload before it burns out your engineers.',
  '/images/landing/landing_page_preview.png'
)

/**
 * Metadata for invitation acceptance page
 */
export function invitationPageMetadata(organizationName: string) {
  return generatePageMetadata(
    `Join ${organizationName} on On-Call Health`,
    `Accept your invitation to ${organizationName} and start monitoring team wellbeing.`,
  )
}
