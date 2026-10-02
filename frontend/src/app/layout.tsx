import type { Metadata, Viewport } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-sans',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-mono',
})

export const metadata: Metadata = {
  title: 'NeuroSeek AI',
  description: 'Self-improving multi-model AI with continuous LoRA fine-tuning',
  keywords: ['AI', 'LLM', 'chat', 'fine-tuning', 'LoRA', 'multi-model'],
  authors: [{ name: 'NeuroSeek Team' }],
  creator: 'NeuroSeek AI',
  publisher: 'NeuroSeek AI',
  robots: 'index, follow',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://neuroseek.ai',
    title: 'NeuroSeek AI',
    description: 'Self-improving multi-model AI with continuous LoRA fine-tuning',
    siteName: 'NeuroSeek AI',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'NeuroSeek AI',
    description: 'Self-improving multi-model AI with continuous LoRA fine-tuning',
  },
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon-16x16.png',
    apple: '/apple-touch-icon.png',
  },
  manifest: '/site.webmanifest',
}

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0f172a' },
  ],
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning className={`${inter.variable} ${jetbrainsMono.variable} antialiased`}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="min-h-screen bg-background font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}