"use client";

import { useSession, useUser, useDescope } from "@descope/nextjs-sdk/client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import ChatPanel from "@/components/dashboard/chat-panel";
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, isSessionLoading, sessionToken } = useSession();
  const { user, isUserLoading } = useUser();
  const sdk = useDescope();

  useEffect(() => {
    if (!isSessionLoading && !isAuthenticated) {
      router.replace("/sign-in");
    }
  }, [isAuthenticated, isSessionLoading, router]);

  if (isSessionLoading || isUserLoading || !sessionToken) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <Skeleton className="h-20 w-80" />
      </div>
    );
  }

  const handleLogout = async () => {
    await sdk.logout();
    router.replace("/sign-in");
  };

  return (
    <ChatPanel
      sessionToken={sessionToken}
      userEmail={user?.email || user?.name}
      onLogout={handleLogout}
    />
  );
}