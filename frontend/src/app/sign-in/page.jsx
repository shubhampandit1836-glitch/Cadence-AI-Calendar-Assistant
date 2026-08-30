"use client";

import RedirectIfAuthenticated from "@/components/auth/RedirectIfAuthenticated";
import SignInComponent from "@/components/auth/sign-in";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles } from "lucide-react";

export default function SignInPage() {
  return (
    <RedirectIfAuthenticated>
      <main className="flex min-h-screen w-full items-center justify-center bg-muted/40 p-4">
        <Card className="w-full max-w-md shadow-lg">
          <CardHeader className="text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
              <Sparkles className="h-6 w-6" />
            </div>
            <CardTitle className="mt-2 text-2xl font-bold">Meeting Assistant</CardTitle>
            <CardDescription>Sign in to sync your Google Calendar with LangGraph AI agents.</CardDescription>
          </CardHeader>
          <CardContent>
            <SignInComponent />
          </CardContent>
        </Card>
      </main>
    </RedirectIfAuthenticated>
  );
}