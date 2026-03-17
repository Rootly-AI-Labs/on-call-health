import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token");

  if (!token) {
    return new NextResponse("Missing token", { status: 400 });
  }

  const backendUrl = `${BACKEND_URL}/api/digests/weekly/unsubscribe?token=${encodeURIComponent(token)}`;

  const response = await fetch(backendUrl);
  const html = await response.text();

  return new NextResponse(html, {
    status: response.status,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
