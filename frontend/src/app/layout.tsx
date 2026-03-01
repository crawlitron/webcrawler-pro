import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '../components/AuthProvider';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'WebCrawler Pro — SEO Crawler',
  description: 'Professional SEO crawler and site auditing tool',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>
          <nav className="border-b bg-white shadow-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex items-center justify-between h-16">
                <a href="/" className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                    <span className="text-white text-xs font-bold">WC</span>
                  </div>
                  <span className="text-xl font-bold text-gray-900">WebCrawler Pro</span>
                </a>
                <div className="hidden sm:flex items-center gap-1">
                  <a href="/" className="px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition">Dashboard</a>
                  <a href="/teams" className="px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition">Teams</a>
                  <a href="/settings" className="px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition">Settings</a>
                  <a href="/settings/integrations" className="px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition">Integrations</a>
                  <a href="/settings/profile" className="px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition">Profile</a>
                </div>
                <div className="sm:hidden text-sm text-gray-500">SEO Crawler</div>
              </div>
            </div>
          </nav>
          <main className="min-h-screen bg-gray-50">{children}</main>
          <footer className="border-t bg-white py-4 text-center text-sm text-gray-400">
            WebCrawler Pro &copy; {new Date().getFullYear()} &mdash; v0.8.0
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
