import { useState, useCallback } from 'react'

const CATEGORY_STYLES = {
  tool: { label: 'Tool', bg: 'bg-violet-500/15 text-violet-400 border-violet-500/30' },
  library: { label: 'Library', bg: 'bg-sky-500/15 text-sky-400 border-sky-500/30' },
  mcp: { label: 'MCP', bg: 'bg-accent-cyan/15 text-accent-cyan border-accent-cyan/30' },
  technique: { label: 'Technique', bg: 'bg-amber-500/15 text-amber-400 border-amber-500/30' },
  product: { label: 'Product', bg: 'bg-accent-orange/15 text-accent-orange border-accent-orange/30' },
  other: { label: 'Other', bg: 'bg-surface-400/20 text-slate-400 border-surface-400/40' },
}

const LABEL_STYLES = {
  relevant: { text: 'Relevant', dot: 'bg-emerald-400', badge: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' },
  maybe: { text: 'Worth a look', dot: 'bg-amber-400', badge: 'bg-amber-500/15 text-amber-400 border-amber-500/30' },
}

const RATING_OPTIONS = [
  { value: 'useful', icon: '👍', label: 'Useful' },
  { value: 'not_useful', icon: '👎', label: 'Not useful' },
  { value: 'skip', icon: '⏭️', label: 'Skip' },
]

const STEPS = [
  { key: 'fetch', label: 'Fetching stories' },
  { key: 'coarse', label: 'Filtering noise' },
  { key: 'relevance', label: 'Scoring relevance' },
  { key: 'done', label: 'Done' },
]

function SpinnerIcon({ className = 'h-4 w-4' }) {
  return (
    <svg className={`animate-spin ${className}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  )
}

function PipelineProgress({ step }) {
  const stepIdx = STEPS.findIndex(s => s.key === step)
  return (
    <div className="flex items-center gap-1 w-full">
      {STEPS.map((s, i) => {
        const active = i === stepIdx
        const done = i < stepIdx
        return (
          <div key={s.key} className="flex items-center gap-1 flex-1">
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium transition-all duration-300 ${active ? 'bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30' :
              done ? 'bg-emerald-500/10 text-emerald-400/70' :
                'text-slate-600'
              }`}>
              {active && <SpinnerIcon className="h-3 w-3" />}
              {done && <span className="text-emerald-400">✓</span>}
              <span>{s.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`flex-1 h-px mx-1 ${done ? 'bg-emerald-500/30' : 'bg-surface-500/30'}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}

function CategoryBadge({ category }) {
  const style = CATEGORY_STYLES[category] || CATEGORY_STYLES.other
  return (
    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${style.bg}`}>
      {style.label}
    </span>
  )
}

function RelevanceBadge({ label }) {
  const style = LABEL_STYLES[label] || LABEL_STYLES.maybe
  return (
    <span className={`flex items-center gap-1.5 text-[11px] font-semibold px-2 py-0.5 rounded-full border ${style.badge}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
      {style.text}
    </span>
  )
}

function RatingButtons({ rating, onRate }) {
  return (
    <div className="flex items-center gap-1">
      {RATING_OPTIONS.map(opt => (
        <button
          key={opt.value}
          onClick={(e) => { e.preventDefault(); onRate(opt.value) }}
          title={opt.label}
          className={`w-7 h-7 rounded-md flex items-center justify-center text-sm transition-all duration-150 cursor-pointer ${rating === opt.value
            ? 'bg-surface-400/60 ring-1 ring-accent-cyan/40 scale-110'
            : 'bg-surface-600/40 hover:bg-surface-500/60 opacity-60 hover:opacity-100'
            }`}
        >
          {opt.icon}
        </button>
      ))}
    </div>
  )
}

function DiscoveryCard({ discovery, rating, onRate, index }) {
  return (
    <div
      className="animate-fade-in-up bg-surface-700/60 backdrop-blur-sm border border-surface-500/50 rounded-xl p-4 hover:border-surface-400/70 hover:bg-surface-700/80 transition-all duration-200 group"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <a
            href={discovery.hn_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-semibold text-slate-200 leading-snug group-hover:text-white transition-colors hover:underline decoration-accent-cyan/40 underline-offset-2"
          >
            {discovery.title}
          </a>
        </div>
        <RatingButtons rating={rating} onRate={onRate} />
      </div>

      <div className="flex items-center gap-2 flex-wrap mb-3">
        <RelevanceBadge label={discovery.label} />
        <CategoryBadge category={discovery.category} />
        <span className="text-[11px] text-slate-500 font-mono">
          {discovery.score}pts &middot; {discovery.num_comments}c &middot; @{discovery.author}
        </span>
      </div>

      <div className="bg-surface-800/60 rounded-lg px-3 py-2 mb-3 border border-surface-500/20">
        <p className="text-xs text-slate-400 leading-relaxed">
          <span className="text-accent-cyan/80 font-semibold mr-1">Why it fits:</span>
          {discovery.reason}
        </p>
      </div>

      {discovery.url && (
        <a
          href={discovery.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-[11px] text-slate-500 hover:text-accent-cyan transition-colors font-mono"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          {discovery.url.replace(/^https?:\/\//, '').slice(0, 60)}
        </a>
      )}

      {discovery.text && (
        <p className="mt-2 text-[11px] text-slate-600 leading-relaxed line-clamp-2 italic">
          {discovery.text.replace(/<[^>]+>/g, ' ').slice(0, 200)}
        </p>
      )}
    </div>
  )
}

function StatsBar({ data }) {
  if (!data) return null
  return (
    <div className="flex items-center gap-4 flex-wrap">
      <Stat label="Scanned" value={data.total_fetched} />
      <Stat label="Relevant" value={data.relevant_count} accent="text-emerald-400" />
      <Stat label="Worth a look" value={data.maybe_count} accent="text-amber-400" />
    </div>
  )
}

function Stat({ label, value, accent = 'text-white' }) {
  return (
    <div className="flex items-center gap-2 bg-surface-700/50 px-3 py-1.5 rounded-lg border border-surface-500/20">
      <span className="text-[10px] text-slate-500 uppercase tracking-widest">{label}</span>
      <span className={`text-sm font-bold font-mono ${accent}`}>{value}</span>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-slate-600">
      <div className="w-16 h-16 rounded-2xl border-2 border-dashed border-surface-500 flex items-center justify-center mb-4">
        <svg className="w-7 h-7 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
        </svg>
      </div>
      <p className="text-sm font-medium text-slate-500">No scan results yet</p>
      <p className="text-xs mt-1 text-slate-700">Click "Run Scout" to scan Hacker News for tools relevant to your product</p>
    </div>
  )
}

export default function FeatureBuilderDashboard() {
  const [data, setData] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [pipelineStep, setPipelineStep] = useState(null)
  const [ratings, setRatings] = useState({})
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')

  const runScout = useCallback(async () => {
    if (scanning) return
    setScanning(true)
    setError(null)
    setPipelineStep('fetch')

    const stepTimer = setTimeout(() => setPipelineStep('coarse'), 3000)
    const stepTimer2 = setTimeout(() => setPipelineStep('relevance'), 9000)

    try {
      const resp = await fetch('/api/scout/run', { method: 'POST' })
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}))
        throw new Error(body.detail || `Scan failed: ${resp.status}`)
      }
      const result = await resp.json()
      setData(result)
      setPipelineStep('done')
    } catch (err) {
      console.error('Scout error:', err)
      setError(err.message)
      setPipelineStep(null)
    } finally {
      clearTimeout(stepTimer)
      clearTimeout(stepTimer2)
      setScanning(false)
    }
  }, [scanning])

  const handleRate = useCallback((id, value) => {
    setRatings(prev => ({ ...prev, [id]: prev[id] === value ? null : value }))
  }, [])

  const discoveries = data?.discoveries || []
  const filtered = filter === 'all'
    ? discoveries
    : discoveries.filter(d => d.label === filter)

  const ratedCount = Object.values(ratings).filter(Boolean).length

  return (
    <div className="min-h-screen bg-surface-900">
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--color-surface-700)_0%,_transparent_50%)] opacity-50" />
        <div className="absolute top-0 right-0 w-96 h-96 bg-accent-cyan/[0.03] rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-accent-orange/[0.03] rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Header */}
        <header className="bg-surface-800/70 backdrop-blur-xl border border-surface-500/30 rounded-2xl p-4 sm:p-5 mb-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent-cyan to-accent-orange flex items-center justify-center shadow-lg shadow-accent-cyan/20">
                <span className="text-base font-black text-surface-900 font-[family-name:var(--font-display)]">C</span>
              </div>
              <div>
                <h1 className="text-lg font-bold text-white tracking-tight font-[family-name:var(--font-display)]">
                  Feature Builder
                </h1>
                <p className="text-[11px] text-slate-500">Scout HN for tools & ideas for <span className="text-slate-400 font-semibold">le Chad</span></p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {data && <StatsBar data={data} />}

              <button
                onClick={runScout}
                disabled={scanning}
                className={`
                  relative flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold
                  transition-all duration-300 cursor-pointer whitespace-nowrap
                  ${scanning
                    ? 'bg-surface-600 text-slate-400 border border-surface-500'
                    : 'bg-gradient-to-r from-accent-cyan to-cyan-400 text-surface-900 shadow-lg shadow-accent-cyan/25 hover:shadow-accent-cyan/40 hover:scale-[1.02] active:scale-[0.98] border border-accent-cyan/50'
                  }
                `}
              >
                {scanning ? (
                  <><SpinnerIcon /> Scanning...</>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                    </svg>
                    Run Scout
                  </>
                )}
              </button>
            </div>
          </div>

          {scanning && pipelineStep && (
            <div className="mt-4">
              <PipelineProgress step={pipelineStep} />
            </div>
          )}
        </header>

        {error && (
          <div className="mb-6 bg-accent-red/10 border border-accent-red/30 rounded-xl p-4 text-sm text-accent-red">
            <span className="font-semibold">Error:</span> {error}
          </div>
        )}

        {/* Filter tabs + rating summary */}
        {discoveries.length > 0 && (
          <div className="flex items-center justify-between mb-5 gap-4 flex-wrap">
            <div className="flex items-center gap-1.5 bg-surface-800/50 border border-surface-500/20 rounded-xl p-1">
              {[
                { key: 'all', label: `All (${discoveries.length})` },
                { key: 'relevant', label: `Relevant (${discoveries.filter(d => d.label === 'relevant').length})` },
                { key: 'maybe', label: `Maybe (${discoveries.filter(d => d.label === 'maybe').length})` },
              ].map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setFilter(tab.key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${filter === tab.key
                    ? 'bg-surface-600 text-white shadow-sm'
                    : 'text-slate-500 hover:text-slate-300'
                    }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {ratedCount > 0 && (
              <span className="text-[11px] text-slate-500 font-mono">
                {ratedCount}/{discoveries.length} rated
              </span>
            )}
          </div>
        )}

        {/* Results */}
        {discoveries.length === 0 && !scanning ? (
          <EmptyState />
        ) : (
          <div className="grid gap-3">
            {filtered.map((d, i) => (
              <DiscoveryCard
                key={d.id}
                discovery={d}
                rating={ratings[d.id]}
                onRate={(value) => handleRate(d.id, value)}
                index={i}
              />
            ))}
          </div>
        )}

        {scanning && discoveries.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20">
            <SpinnerIcon className="h-8 w-8 text-accent-cyan mb-4" />
            <p className="text-sm text-slate-400">Scanning Hacker News...</p>
            <p className="text-xs text-slate-600 mt-1">This usually takes 15-30 seconds</p>
          </div>
        )}

        <footer className="mt-8 pb-4 text-center">
          <p className="text-[11px] text-slate-700 font-mono tracking-wider">
            CHADBOT FEATURE BUILDER v1.0
          </p>
        </footer>
      </div>
    </div>
  )
}
