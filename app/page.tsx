'use client'
import { useEffect, useMemo, useState } from 'react'
import {
  ArrowDownRight,
  ArrowUpRight,
  Bell,
  Check,
  ChevronDown,
  CircleHelp,
  FileText,
  FileImage,
  FileSpreadsheet,
  Gauge,
  LayoutDashboard,
  Lightbulb,
  LockKeyhole,
  MoreHorizontal,
  Plus,
  ReceiptText,
  Search,
  Settings2,
  Sparkles,
  UploadCloud,
  WalletCards,
  X,
} from 'lucide-react'

type Transaction = { date: string; merchant: string; amount: number; category: string; type: 'income' | 'expense' }
type AnalysisResult = { processed_files: string[]; transaction_count: number; summary: { summary?: Record<string, { total: number; count: number }>; top_categories?: { category: string; total: number; count: number }[]; recent_transactions?: Transaction[] }; chart_data?: Transaction[] }

const categoryColors = ['bg-chart-1', 'bg-chart-2', 'bg-chart-3', 'bg-chart-4', 'bg-chart-5']

export default function Page() {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [showPanel, setShowPanel] = useState(false)
  const [activeNav, setActiveNav] = useState('Overview')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [processing, setProcessing] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [insights, setInsights] = useState('')
  const [insightsLoading, setInsightsLoading] = useState(false)

  const transactions = analysis?.summary.recent_transactions ?? []
  const chartData = analysis?.chart_data ?? transactions

  const chartPoints = useMemo(() => {
    const grouped = new Map<string, { date: string; income: number; expense: number }>()
    chartData.forEach((item) => {
      const key = item.date?.slice(0, 7) || 'Unknown'
      const point = grouped.get(key) ?? { date: key, income: 0, expense: 0 }
      point[item.type === 'income' ? 'income' : 'expense'] += Number(item.amount) || 0
      grouped.set(key, point)
    })
    return Array.from(grouped.values())
      .filter((point) => point.income > 0 || point.expense > 0)
      .sort((a, b) => a.date.localeCompare(b.date))
      .slice(-12)
  }, [chartData])

  // ✅ NEW: cumulative net cash flow per month for the line graph
  const cashFlowSeries = useMemo(() => {
    let running = 0
    return chartPoints.map((point) => {
      const net = point.income - point.expense
      running += net
      return { date: point.date, net, cumulative: running }
    })
  }, [chartPoints])

  const income = transactions.filter((item) => item.type === 'income').reduce((sum, item) => sum + item.amount, 0)
  const expenses = transactions.filter((item) => item.type === 'expense').reduce((sum, item) => sum + item.amount, 0)
  const categories = analysis?.summary.top_categories ?? []
  const totalSpent = categories.reduce((sum, item) => sum + item.total, 0)
  const health = analysis ? Math.max(0, Math.min(100, Math.round(70 + (income > expenses ? 12 : -8)))) : 0
  const formatMoney = (value: number) => `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  const compactMoney = (value: number) => value >= 1000 ? `$${(value / 1000).toFixed(1)}k` : `$${Math.round(value)}`
  const monthLabel = (key: string) => {
    const d = new Date(`${key}-01T00:00:00`)
    return isNaN(d.getTime()) ? key : d.toLocaleString('en-US', { month: 'short' })
  }

  function handleFiles(files: FileList | null) {
    if (!files) return
    setSelectedFiles(Array.from(files).slice(0, 8))
  }

  async function loadInsights() {
    if (!analysis || insightsLoading) return
    setInsightsLoading(true)
    try {
      const response = await fetch('/api/insights', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(analysis) })
      const text = await response.text()
      let result: { text?: string; detail?: string } = {}
      try { result = text ? JSON.parse(text) : {} } catch { result = { detail: text.slice(0, 300) } }
      
      if (!response.ok) throw new Error(result.detail ?? 'Gemini insights are unavailable.')
      setInsights(result.text ?? '')
    } catch (error) {
      setInsights(error instanceof Error ? error.message : 'Could not load insights.')
    } finally {
      setInsightsLoading(false)
    }
  }

  async function handleUpload() {
    if (!selectedFiles.length || processing) return
    setProcessing(true)
    setUploadError('')
    try {
      const formData = new FormData()
      selectedFiles.forEach((file) => formData.append('files', file))
      const response = await fetch('/api/analyze', { method: 'POST', body: formData })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail ?? 'The Python service could not analyze these files.')
      setAnalysis(result as AnalysisResult)
      await refreshAnalysis()   // ✅ re-read full ClickHouse aggregates so every upload visibly updates the dashboard
      setSelectedFiles([])
      setShowPanel(false)
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Analysis failed. Check that the Python API is running.')
    } finally {
      setProcessing(false)
    }
  }

  async function refreshAnalysis() {
    try {
      const res = await fetch('/api/bootstrap')
      if (!res.ok) return
      const data = await res.json()
      if ((data.transaction_count ?? 0) > 0) setAnalysis(data as AnalysisResult)
    } catch { /* backend offline: keep current state */ }
  }

  // ✅ First load: show persisted ClickHouse data (or seed the sample statement)
  useEffect(() => {
    refreshAnalysis()
  }, [])

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen max-w-[1500px]">
        <aside className="hidden w-64 shrink-0 border-r border-border px-5 py-6 lg:flex lg:flex-col">
          <div className="flex items-center gap-3 px-2">
            <div className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground"><WalletCards size={19} /></div>
            <div><p className="font-semibold tracking-tight">MoneyPilot</p><p className="text-xs text-muted-foreground">Personal finance, clear.</p></div>
          </div>
          <div className="mt-10 flex flex-1 flex-col gap-1">
            <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Workspace</p>
            {[['Overview', LayoutDashboard], ['Transactions', ReceiptText], ['Insights', Lightbulb]].map(([label, Icon]) => (
              <button key={label as string} onClick={() => setActiveNav(label as string)} className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${activeNav === label ? 'bg-accent font-medium text-accent-foreground' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}`}><Icon size={17} />{label as string}</button>
            ))}
            <p className="mb-3 mt-8 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Manage</p>
            <button onClick={() => setShowPanel(true)} className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"><UploadCloud size={17} />Upload data</button>
            <button className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"><Settings2 size={17} />Settings</button>
          </div>
          <div className="rounded-xl border border-border bg-muted/40 p-4"><div className="mb-3 flex items-center gap-2 text-xs font-medium"><LockKeyhole size={14} />Private by design</div><p className="text-xs leading-5 text-muted-foreground">Your documents stay yours. MoneyPilot only analyzes what you choose to upload.</p></div>
        </aside>

        <section className="min-w-0 flex-1">
          <header className="flex h-20 items-center justify-between border-b border-border px-6 md:px-10">
            <div><p className="text-sm text-muted-foreground">Monday, September 7, 2026</p><h1 className="text-xl font-semibold tracking-tight">Good morning, Alex</h1></div>
            <div className="flex items-center gap-2"><button className="hidden rounded-lg border border-border p-2 text-muted-foreground hover:bg-muted sm:block"><Search size={18} /></button><button className="relative rounded-lg border border-border p-2 text-muted-foreground hover:bg-muted"><Bell size={18} /><span className="absolute right-1.5 top-1.5 size-1.5 rounded-full bg-primary" /></button><div className="ml-2 flex size-9 items-center justify-center rounded-full bg-accent text-sm font-semibold">AM</div></div>
          </header>

          <div className="space-y-6 p-6 md:p-10">
            {activeNav !== 'Overview' && <section className="rounded-2xl border border-border bg-card p-5 md:p-6">
              <div className="mb-6 flex items-start justify-between"><div><p className="mb-1 text-sm font-medium text-primary">Workspace</p><h2 className="text-3xl font-semibold tracking-tight">{activeNav}</h2><p className="mt-2 text-sm text-muted-foreground">{activeNav === 'Transactions' ? 'Every transaction extracted from your uploaded files.' : 'Gemini-generated recommendations grounded in your analyzed transactions.'}</p></div><button onClick={() => setActiveNav('Overview')} className="rounded-lg border border-border px-3 py-2 text-sm hover:bg-muted">Back to overview</button></div>
              {activeNav === 'Transactions' ? <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b border-border text-muted-foreground"><tr><th className="px-3 py-3">Date</th><th className="px-3 py-3">Merchant</th><th className="px-3 py-3">Category</th><th className="px-3 py-3 text-right">Amount</th></tr></thead><tbody>{transactions.map((item, index) => <tr key={`${item.date}-${item.merchant}-${index}`} className="border-b border-border/60"><td className="px-3 py-3">{item.date}</td><td className="px-3 py-3 font-medium">{item.merchant}</td><td className="px-3 py-3 text-muted-foreground">{item.category}</td><td className="px-3 py-3 text-right">{formatMoney(item.amount)}</td></tr>)}</tbody></table>{!transactions.length && <p className="py-12 text-center text-sm text-muted-foreground">Upload a statement to populate transactions.</p>}</div> : <div><button onClick={loadInsights} disabled={!analysis || insightsLoading} className="rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50">{insightsLoading ? 'Asking Gemini…' : insights ? 'Refresh Gemini insights' : 'Generate Gemini insights'}</button>{insights ? <pre className="mt-6 whitespace-pre-wrap rounded-xl bg-muted/50 p-5 text-sm leading-6">{insights}</pre> : <p className="mt-6 text-sm text-muted-foreground">{analysis ? 'Generate recommendations from your uploaded data.' : 'Upload and analyze data before requesting insights.'}</p>}</div>}
            </section>}

            {activeNav === 'Overview' && <>
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="mb-1 text-sm font-medium text-primary">Your financial cockpit</p><h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Cash-flow health</h2><p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">A calm view of what is coming in, going out, and what you can do next.</p></div><button onClick={() => setShowPanel(true)} className="flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-sm hover:opacity-90"><Plus size={17} />Add statement</button></div>

            <div className="grid gap-4 md:grid-cols-3">
              <article className="rounded-2xl border border-border bg-card p-5"><div className="mb-6 flex items-center justify-between"><span className="text-sm text-muted-foreground">Available balance</span><span className="rounded-md bg-accent px-2 py-1 text-xs font-medium text-accent-foreground">Healthy</span></div><p className="text-3xl font-semibold tracking-tight">{analysis ? formatMoney(Math.max(0, income - expenses)) : '—'}</p><div className="mt-3 flex items-center gap-1 text-sm text-muted-foreground">{analysis ? `${transactions.length} transactions analyzed` : 'Upload data to calculate'}</div></article>
              <article className="rounded-2xl border border-border bg-card p-5"><div className="mb-6 flex items-center justify-between"><span className="text-sm text-muted-foreground">Projected month-end</span><Gauge size={18} className="text-muted-foreground" /></div><p className="text-3xl font-semibold tracking-tight">{analysis ? formatMoney(income - expenses) : '—'}</p><div className="mt-3 flex items-center gap-1 text-sm text-muted-foreground">{analysis ? 'Current analyzed period' : 'Waiting for your data'}</div></article>
              <article className="rounded-2xl border border-border bg-primary p-5 text-primary-foreground"><div className="mb-5 flex items-center justify-between"><span className="text-sm opacity-75">MoneyPilot score</span><Sparkles size={18} /></div><div className="flex items-end gap-3"><p className="text-4xl font-semibold tracking-tight">{health}</p><p className="mb-1 text-sm opacity-75">/ 100</p></div><div className="mt-4 h-1.5 overflow-hidden rounded-full bg-primary-foreground/20"><div className="h-full rounded-full bg-primary-foreground" style={{ width: `${health}%` }} /></div><p className="mt-3 text-xs opacity-75">{analysis ? 'Your uploaded data powers this score.' : 'Upload a statement to calculate your score.'}</p></article>
            </div>

            <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
              <article className="rounded-2xl border border-border bg-card p-5 md:p-6">
                <div className="mb-8 flex items-start justify-between">
                  <div><h3 className="font-semibold">Cash in, cash out</h3><p className="mt-1 text-sm text-muted-foreground">Months with activity · income vs expenses</p></div>
                  <button className="flex items-center gap-1 text-sm text-muted-foreground">This year <ChevronDown size={15} /></button>
                </div>
                <div className="flex h-52 items-end justify-center gap-2 border-b border-border px-2 md:gap-4">
                  {analysis && chartPoints.length ? chartPoints.map((point) => {
                    const maxAmount = Math.max(...chartPoints.flatMap((entry) => [entry.income, entry.expense]), 1)
                    const incomeHeight = point.income ? Math.max(10, (point.income / maxAmount) * 88) : 0
                    const expenseHeight = point.expense ? Math.max(10, (point.expense / maxAmount) * 88) : 0
                    return (
                      <div key={point.date} className="group flex h-full min-w-0 max-w-24 flex-1 items-end justify-center gap-1">
                        <div className="relative flex h-full w-1/2 items-end justify-center">
                          <div className="w-full rounded-t-sm bg-primary transition-all" style={{ height: `${incomeHeight}%` }} title={`${point.date} income: ${formatMoney(point.income)}`} />
                          <span className={`pointer-events-none absolute left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] font-semibold ${point.income ? 'text-foreground' : 'text-muted-foreground'}`} style={{ bottom: `calc(${incomeHeight}% + 4px)` }}>{compactMoney(point.income)}</span>
                        </div>
                        <div className="relative flex h-full w-1/2 items-end justify-center">
                          <div className="w-full rounded-t-sm bg-chart-2 transition-all" style={{ height: `${expenseHeight}%` }} title={`${point.date} expenses: ${formatMoney(point.expense)}`} />
                          <span className={`pointer-events-none absolute left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] font-semibold ${point.expense ? 'text-chart-2' : 'text-muted-foreground'}`} style={{ bottom: `calc(${expenseHeight}% + 4px)` }}>{compactMoney(point.expense)}</span>
                        </div>
                      </div>
                    )
                  }) : <div className="flex h-full w-full items-center justify-center text-sm text-muted-foreground">Upload a statement to see your cash flow</div>}
                </div>
                <div className="mt-3 flex justify-center gap-2 px-2 md:gap-4">
                  {chartPoints.length ? chartPoints.map((point) => (
                    <span key={point.date} className="min-w-0 max-w-24 flex-1 truncate text-center text-xs text-muted-foreground">{monthLabel(point.date)}</span>
                  )) : <span className="flex-1 text-center text-xs text-muted-foreground">—</span>}
                </div>
                <div className="mt-6 flex gap-5 text-xs text-muted-foreground">
                  <span className="flex items-center gap-2"><i className="size-2 rounded-full bg-primary" />Income</span>
                  <span className="flex items-center gap-2"><i className="size-2 rounded-full bg-chart-2" />Expenses</span>
                </div>
              </article>

              <article className="rounded-2xl border border-border bg-card p-5 md:p-6"><div className="mb-7 flex items-start justify-between"><div><h3 className="font-semibold">Spending habits</h3><p className="mt-1 text-sm text-muted-foreground">{analysis ? `${formatMoney(totalSpent)} total analyzed` : 'No spending data yet'}</p></div><button className="text-muted-foreground"><MoreHorizontal size={19} /></button></div><div className="mb-8 flex items-center justify-center"><div className="relative flex size-44 items-center justify-center rounded-full" style={{ background: categories.length ? `conic-gradient(${categories.map((item, index) => { const start = categories.slice(0, index).reduce((sum, category) => sum + category.total, 0) / Math.max(totalSpent, 1) * 100; const end = (categories.slice(0, index + 1).reduce((sum, category) => sum + category.total, 0) / Math.max(totalSpent, 1)) * 100; return `var(--chart-${(index % 5) + 1}) ${start}% ${end}%` }).join(', ')})` : 'var(--muted)' }}><div className="flex size-28 flex-col items-center justify-center rounded-full bg-card"><span className="text-2xl font-semibold">{formatMoney(totalSpent)}</span><span className="text-xs text-muted-foreground">spent</span></div></div></div><div className="space-y-3">{categories.length ? categories.map((item, index) => <div key={item.category} className="flex items-center justify-between text-sm"><span className="flex items-center gap-2 text-muted-foreground"><i className={`size-2 rounded-full ${categoryColors[index % categoryColors.length]}`} />{item.category}</span><span className="font-medium">{formatMoney(item.total)}</span></div>) : <p className="text-sm text-muted-foreground">Upload data to see spending habits.</p>}</div></article>
            </div>

            {/* ✅ NEW ARTICLE: CASH-FLOW LINE GRAPH (below the two charts) */}
            <article className="rounded-2xl border border-border bg-card p-5 md:p-6">
              <div className="mb-6 flex items-start justify-between">
                <div>
                  <h3 className="font-semibold">Cash flow trend</h3>
                  <p className="mt-1 text-sm text-muted-foreground">Cumulative net cash flow across your analyzed months</p>
                </div>
                {cashFlowSeries.length > 0 && (
                  <span className="rounded-md bg-accent px-2 py-1 text-xs font-medium text-accent-foreground">
                    {cashFlowSeries[cashFlowSeries.length - 1].cumulative >= 0 ? '+' : '-'}{compactMoney(Math.abs(cashFlowSeries[cashFlowSeries.length - 1].cumulative))} net
                  </span>
                )}
              </div>
              {analysis && cashFlowSeries.length > 1 ? (() => {
                const values = cashFlowSeries.map((p) => p.cumulative)
                const min = Math.min(...values, 0)
                const max = Math.max(...values, 0)
                const span = max - min || 1
                const px = (i: number) => 40 + i * (520 / (cashFlowSeries.length - 1))
                const py = (v: number) => 180 - ((v - min) / span) * 145
                const zeroY = py(0)
                const linePoints = cashFlowSeries.map((p, i) => `${px(i)},${py(p.cumulative)}`).join(' ')
                const areaPath = `M ${px(0)},${py(cashFlowSeries[0].cumulative)} ` + cashFlowSeries.slice(1).map((p, i) => `L ${px(i + 1)},${py(p.cumulative)}`).join(' ') + ` L ${px(cashFlowSeries.length - 1)},${zeroY} L ${px(0)},${zeroY} Z`
                return (
                  <svg viewBox="0 0 600 215" className="w-full">
                    <line x1="40" y1={zeroY} x2="560" y2={zeroY} className="stroke-border" strokeWidth="1" strokeDasharray="4 4" />
                    <path d={areaPath} className="fill-chart-2/10" />
                    <polyline points={linePoints} fill="none" className="stroke-chart-2" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
                    {cashFlowSeries.map((p, i) => (
                      <g key={p.date}>
                        <circle cx={px(i)} cy={py(p.cumulative)} r="4" className="fill-chart-2" />
                        <text x={px(i)} y={py(p.cumulative) - 10} textAnchor="middle" className="fill-foreground" fontSize="11" fontWeight="600">{compactMoney(p.cumulative)}</text>
                        <text x={px(i)} y={207} textAnchor="middle" className="fill-muted-foreground" fontSize="11">{monthLabel(p.date)}</text>
                      </g>
                    ))}
                  </svg>
                )
              })() : <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">{analysis ? 'Need at least two months of data to draw the trend line.' : 'Upload a statement to see your cash flow trend'}</div>}
              <div className="mt-4 flex gap-5 text-xs text-muted-foreground">
                <span className="flex items-center gap-2"><i className="size-2 rounded-full bg-chart-2" />Cumulative net cash flow</span>
                <span className="flex items-center gap-2"><i className="h-0 w-4 border-t border-dashed border-border" />Zero line</span>
              </div>
            </article>

            <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
              <article className="rounded-2xl border border-border bg-card p-5 md:p-6">
                <div className="mb-5 flex items-center justify-between">
                  <div><h3 className="font-semibold">Recent transactions</h3><p className="mt-1 text-sm text-muted-foreground">Latest activity from your analyzed files</p></div>
                  <button onClick={() => setActiveNav('Transactions')} className="text-sm font-medium text-primary">View all</button>
                </div>
                <div className="space-y-1">
                  {transactions.slice(0, 4).map((item, index) => (
                    <div key={`${item.date}-${item.merchant}-${index}`} className="flex items-center justify-between rounded-xl px-3 py-3 hover:bg-muted">
                      <div className="flex items-center gap-3">
                        <div className="flex size-9 items-center justify-center rounded-lg bg-muted"><ReceiptText size={16} className="text-muted-foreground" /></div>
                        <div><p className="text-sm font-medium">{item.merchant}</p><p className="text-xs text-muted-foreground">{item.date} · {item.category}</p></div>
                      </div>
                      <span className={`text-sm font-medium ${item.type === 'income' ? 'text-chart-2' : ''}`}>{item.type === 'income' ? '+' : '-'}{formatMoney(item.amount)}</span>
                    </div>
                  ))}
                  {!analysis && <p className="px-3 py-4 text-sm text-muted-foreground">No transactions loaded yet.</p>}
                </div>
              </article>
              <article className="rounded-2xl border border-primary/20 bg-accent/40 p-5 md:p-6"><div className="mb-5 flex items-center gap-2 text-sm font-semibold"><div className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground"><Sparkles size={14} /></div>MoneyPilot recommendation</div><p className="text-lg font-medium leading-7 tracking-tight">{analysis ? <>You have {formatMoney(Math.max(income - expenses, 0))} available after analyzed expenses.</> : 'Upload your financial data to receive a recommendation.'}</p><p className="mt-3 text-sm leading-6 text-muted-foreground">{analysis ? `MoneyPilot analyzed ${transactions.length} transactions across ${categories.length} spending categories.` : 'Recommendations are based only on your uploaded files.'}</p>
              <button onClick={() => { setActiveNav('Insights'); if (analysis && !insights && !insightsLoading) loadInsights() }} className="mt-5 flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium hover:bg-muted">Review opportunities <ArrowUpRight size={15} /></button></article>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-5 text-xs text-muted-foreground"><span className="flex items-center gap-2"><span className={`size-2 rounded-full ${analysis ? 'bg-chart-2' : 'bg-chart-4'}`} />{analysis ? `${analysis.processed_files.length} file${analysis.processed_files.length === 1 ? '' : 's'} analyzed · ClickHouse analytics synced` : 'No financial data loaded · Upload a statement to begin'}</span><button className="flex items-center gap-1 hover:text-foreground"><CircleHelp size={14} />How this works</button></div>
            </>}
          </div>
        </section>
      </div>

      {showPanel && <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/20 p-4 backdrop-blur-sm"><div className="w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl"><div className="flex items-start justify-between"><div><h2 className="text-xl font-semibold">Add financial data</h2><p className="mt-1 text-sm text-muted-foreground">PDFs are extracted locally. ClickHouse powers your insights.</p></div><button onClick={() => setShowPanel(false)} className="rounded-lg p-2 text-muted-foreground hover:bg-muted"><X size={18} /></button></div><label className="mt-7 flex w-full cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-primary/40 bg-accent/30 px-5 py-10 text-center hover:bg-accent"><UploadCloud size={26} className="mb-3 text-primary" /><span className="text-sm font-medium">Drop files or browse your computer</span><span className="mt-1 text-xs text-muted-foreground">Bank PDFs, CSV exports, or receipt images · up to 10 MB each</span><input className="sr-only" type="file" multiple accept=".pdf,.csv,.png,.jpg,.jpeg,.webp" onChange={(event) => handleFiles(event.target.files)} /></label>{selectedFiles.length > 0 && <div className="mt-4 space-y-2">{selectedFiles.map((file) => <div key={`${file.name}-${file.size}`} className="flex items-center justify-between rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm"><span className="flex min-w-0 items-center gap-2"><span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-background">{file.type === 'text/csv' ? <FileSpreadsheet size={15} className="text-primary" /> : file.type.startsWith('image/') ? <FileImage size={15} className="text-chart-3" /> : <FileText size={15} className="text-muted-foreground" />}</span><span className="truncate">{file.name}</span></span><span className="ml-3 shrink-0 text-xs text-muted-foreground">{(file.size / 1024 / 1024).toFixed(1)} MB</span></div>)}</div>}<div className="mt-5 flex items-center gap-3 rounded-lg bg-muted/60 p-3 text-xs leading-5 text-muted-foreground"><LockKeyhole size={15} className="shrink-0" />Files are processed locally by your Python extractor, then synced to ClickHouse for charts.</div>{uploadError && <div role="alert" className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm leading-5 text-destructive">{uploadError}</div>}{analysis && !uploadError && <div className="mt-5 flex items-center gap-2 text-sm font-medium text-chart-2"><Check size={16} />Last upload: {analysis.processed_files.length} file{analysis.processed_files.length === 1 ? '' : 's'} analyzed successfully</div>}<button onClick={handleUpload} disabled={!selectedFiles.length || processing} className="mt-6 w-full rounded-lg bg-primary py-2.5 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50">{processing ? 'Analyzing files…' : 'Analyze files'}</button></div></div>}
    </main>
  )
}