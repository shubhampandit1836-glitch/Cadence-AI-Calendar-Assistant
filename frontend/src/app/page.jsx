"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@descope/nextjs-sdk/client";

export default function HomePage() {
  const router = useRouter();
  const { isAuthenticated, isSessionLoading } = useSession();

  useEffect(() => {
    if (!isSessionLoading) {
      if (isAuthenticated) {
        router.replace("/dashboard");
      } else {
        router.replace("/sign-in");
      }
    }
  }, [isAuthenticated, isSessionLoading, router]);

  return null;
}