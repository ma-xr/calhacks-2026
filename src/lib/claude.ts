// Shared Claude API client. Import this wherever you need to call Claude
// instead of creating new Anthropic clients in multiple places.
//
// Requires ANTHROPIC_API_KEY to be set in .env.local (see .env.example).

import Anthropic from "@anthropic-ai/sdk";

const apiKey = process.env.ANTHROPIC_API_KEY;

if (!apiKey) {
  console.warn(
    "ANTHROPIC_API_KEY is not set. Add it to .env.local to use Claude."
  );
}

export const anthropic = new Anthropic({ apiKey });

// Example helper — adjust model/params to whatever the project needs.
export async function askClaude(prompt: string) {
  const message = await anthropic.messages.create({
    model: "claude-sonnet-5",
    max_tokens: 1024,
    messages: [{ role: "user", content: prompt }],
  });

  return message.content;
}
