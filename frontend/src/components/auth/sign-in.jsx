"use client";

import { Descope } from "@descope/nextjs-sdk";
import { useRouter } from "next/navigation";

export default function SignInComponent() {
  const router = useRouter();

  return (
    <div className="w-full">
      <Descope
        flowId="sign-up-or-in"
        onSuccess={() => {
          router.replace("/dashboard");
        }}
        onError={(e) => {
          console.error("Descope Authentication error:", e);
        }}
      />
    </div>
  );
}