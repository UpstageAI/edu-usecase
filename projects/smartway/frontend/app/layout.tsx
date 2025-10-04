import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Route Visualization',
  description: 'Bus route visualization with React Flow',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
