"use client";

import { useSession } from "@descope/nextjs-sdk/client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Skeleton } from "@/components/ui/skeleton";

export default function RedirectIfAuthenticated({ children }) {
  const { isAuthenticated, isSessionLoading } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (!isSessionLoading && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, isSessionLoading, router]);

  if (isSessionLoading || isAuthenticated) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center gap-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-6 w-48" />
      </div>
    );
  }

  return <>{children}</>;
}