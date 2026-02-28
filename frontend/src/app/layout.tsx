import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "WebCrawler Pro — SEO Crawler",
  description: "Professional SEO crawler and site auditing tool",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <nav className="border-b bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <a href="/" className="flex items-center gap-2">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                  <span className="text-white text-xs font-bold">WC</span>
                </div>
                <span className="text-xl font-bold text-gray-900">WebCrawler Pro</span>
              </a>
              <div className="text-sm text-gray-500">SEO Crawler &amp; Site Auditor</div>
            </div>
          </div>
        </nav>
        <main className="min-h-screen bg-gray-50">{children}</main>
        <footer className="border-t bg-white py-4 text-center text-sm text-gray-400">
          WebCrawler Pro © {new Date().getFullYear()} — Professional SEO Crawler
        </footer>
      </body>
    </html>
  );
}
