// app/api/insights/route.ts
import { NextResponse } from 'next/server'

export const maxDuration = 120

export async function POST(request: Request) {
  const backendUrl = (process.env.PYTHON_API_URL ?? process.env.PYTHON_SERVER_URL ?? process.env.MONEY_PILOT_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')
  
  try {
    const payload = await request.json().catch(() => ({}))
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 110_000)
    
    // Forward the request to your live Python FastAPI backend
    const response = await fetch(`${backendUrl}/insights`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    })
    
    clearTimeout(timeout)
    const text = await response.text()
    let data: unknown
    try {
      data = text ? JSON.parse(text) : { detail: 'The Python insights service returned an empty response.' }
    } catch {
      data = { detail: text.slice(0, 500) }
    }
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    const detail = error instanceof DOMException && error.name === 'AbortError'
      ? 'Gemini insights timed out after 110 seconds.'
      : `Could not reach the Python insights API at ${backendUrl}.`
    return NextResponse.json({ detail }, { status: 502 })
  }
}