// Example API route showing how to call Claude from the backend.
// Delete or rewrite once the real feature is decided.

import { NextRequest, NextResponse } from "next/server";
import { askClaude } from "@/lib/claude";

export async function POST(req: NextRequest) {
  const { prompt } = await req.json();

  if (!prompt || typeof prompt !== "string") {
    return NextResponse.json({ error: "Missing prompt" }, { status: 400 });
  }

  const content = await askClaude(prompt);
  return NextResponse.json({ content });
}
