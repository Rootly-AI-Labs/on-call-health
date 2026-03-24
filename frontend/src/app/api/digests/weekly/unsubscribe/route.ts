import { NextRequest, NextResponse } from "next/server";

// Legacy GET handler — redirect to the confirmation page instead of auto-unsubscribing
export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token");

  if (!token) {
    return new NextResponse("Missing token", { status: 400 });
  }

  const redirectUrl = new URL("/unsubscribe", request.nextUrl.origin);
  redirectUrl.searchParams.set("token", token);

  return NextResponse.redirect(redirectUrl.toString(), { status: 302 });
}
