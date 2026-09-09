import { NextResponse } from 'next/server'

export const maxDuration = 120

export async function POST(request: Request) {
  // ✅ FIX: Bracket notation + live fallback
  const backendUrl = (
    process.env["PYTHON_API_URL"] ?? 
    process.env["PYTHON_SERVER_URL"] ?? 
    'https://moneypilot-api-722080548291.us-central1.run.app'
  ).replace(/\/$/, '')

  const formData = await request.formData()
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 110_000)

  try {
    const response = await fetch(`${backendUrl}/analyze`, {
      method: 'POST',
      body: formData,
      signal: controller.signal,
    })
    const body = await response.json().catch(() => ({ detail: 'The Python service returned an invalid response.' }))
    return NextResponse.json(body, { status: response.status })
  } catch (error) {
    const detail = error instanceof DOMException && error.name === 'AbortError'
      ? 'Analysis timed out after 110 seconds.'
      : `Could not reach the Python API at ${backendUrl}.`
    return NextResponse.json({ detail }, { status: 502 })
  } finally {
    clearTimeout(timeout)
  }
}