import { NextResponse } from 'next/server'

const EMPTY = { processed_files: [], transaction_count: 0, summary: { summary: {}, top_categories: [], recent_transactions: [] }, chart_data: [] }

export async function GET() {
  // ✅ FIX: Bracket notation + live fallback
  const urls = [
  process.env["PYTHON_SERVER_URL"],
  'https://moneypilot-api-722080548291.us-central1.run.app',
  'http://127.0.0.1:8000',
  ].filter(Boolean) as string[]

  for (const baseUrl of urls) {
    const base = baseUrl.replace(/\/$/, '')
    try {
      const res = await fetch(`${base}/summary`, { cache: 'no-store' })
      if (res.ok) {
        const data = await res.json()
        if ((data.transaction_count ?? 0) > 0) return NextResponse.json(data)
      }
      const seed = await fetch(`${base}/seed`, { method: 'POST' })
      if (seed.ok) {
        const data = await seed.json()
        if ((data.transaction_count ?? 0) > 0) return NextResponse.json(data)
      }
      return NextResponse.json(EMPTY)
    } catch {
      continue
    }
  }
  return NextResponse.json(EMPTY, { status: 502 })
}