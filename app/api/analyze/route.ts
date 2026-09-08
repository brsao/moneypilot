import { NextResponse } from 'next/server'

export const maxDuration = 120

export async function POST(request: Request) {
  const configuredUrl = process.env.PYTHON_API_URL ?? process.env.PYTHON_SERVER_URL ?? process.env.PYTHON_API_URL_2 ?? process.env.PYTHON_SERVER_URL_2 ?? process.env.MONEY_PILOT_API_URL ?? 'http://127.0.0.1:8000'
  const normalizedUrl = configuredUrl.replace(/\/$/, '')
  const urls = normalizedUrl.includes('localhost')
    ? [normalizedUrl.replace('localhost', '127.0.0.1'), normalizedUrl]
    : [normalizedUrl]
  const formData = await request.formData()
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 110_000)

  try {
    let response: Response | undefined
    let lastError: unknown
    for (const url of urls) {
      try {
        response = await fetch(`${url}/analyze`, { method: 'POST', body: formData, signal: controller.signal })
        break
      } catch (error) {
        lastError = error
      }
    }
    if (!response) {
      const message = lastError instanceof Error ? lastError.message : 'Unknown connection error'
      throw new Error(`${message}. Tried: ${urls.join(', ')}`)
    }
    const body = await response.json().catch(() => ({ detail: 'The Python service returned an invalid response.' }))
    return NextResponse.json(body, { status: response.status })
  } catch (error) {
    const isTimeout = error instanceof DOMException && error.name === 'AbortError'
    const detail = isTimeout
      ? 'Analysis timed out after 110 seconds. Check the Python terminal for the extraction or ClickHouse error.'
      : `Could not reach the Python API. ${error instanceof Error ? error.message : 'Confirm Uvicorn is running on port 8000.'}`
    return NextResponse.json({ detail }, { status: 502 })
  } finally {
    clearTimeout(timeout)
  }
}
