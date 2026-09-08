import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  const backendUrl = process.env.MONEY_PILOT_API_URL ?? 'http://127.0.0.1:8000'
  const payload = await request.json()
  const response = await fetch(`${backendUrl}/insights`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const body = await response.json().catch(() => ({ detail: 'The Python service returned an invalid response.' }))
  return NextResponse.json(body, { status: response.status })
}