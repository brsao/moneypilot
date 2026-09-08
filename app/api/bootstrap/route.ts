import { NextResponse } from 'next/server'

const EMPTY = { processed_files: [], transaction_count: 0, summary: { summary: {}, top_categories: [], recent_transactions: [] }, chart_data: [] }

export async function GET() {
  const urls = [
    process.env.PYTHON_API_URL,
    process.env.PYTHON_SERVER_URL,
    'http://127.0.0.1:8000',   // ✅ IPv4 first — no more ECONNREFUSED ::1 noise
    'http://localhost:8000'
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