import { Inter } from "next/font/google";
import { AuthProvider } from "@descope/nextjs-sdk";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export const metadata = {
  title: "Cadence — AI Calendar Assistant",
  description: "Cadence keeps your schedule sorted.",
};

export default function RootLayout({ children }) {
  const projectId = process.env.NEXT_PUBLIC_DESCOPE_PROJECT_ID || "";

  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        <ThemeProvider>
          <AuthProvider
            projectId={projectId}
            sessionTokenViaCookie={true}
            refreshTokenViaCookie={true}
          >
            {children}
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}