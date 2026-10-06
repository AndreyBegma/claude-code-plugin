import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '__TITLE__',
  description: '__TITLE__',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
