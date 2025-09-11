import type { FullConfig } from '@playwright/test';

export default async function globalSetup(_config: FullConfig) {
  const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost';
  const token = process.env.NEXT_PUBLIC_API_TOKEN || 'dev-token';
  const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } as const;

  // Seed a couple of library assets for Attach Assets tests
  try {
    await fetch(`${base}/api/v1/library/assets`, { method: 'POST', headers, body: JSON.stringify({ label: 'kb_greeting', content: 'hello world', mime: 'text/plain', org_id: 'demo_org', user_id: 'demo_user' }) });
  } catch {}
  try {
    await fetch(`${base}/api/v1/library/assets`, { method: 'POST', headers, body: JSON.stringify({ label: 'kb_resume', content: 'experience...', mime: 'text/plain', org_id: 'demo_org', user_id: 'demo_user' }) });
  } catch {}
}
