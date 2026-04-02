import { useState, useCallback } from 'react'
import './index.css'

// ── Mock data pools ──────────────────────────────────────────────────────────

const BUG_TITLES = [
  "Bot fails to respond after 10+ messages in a thread",
  "Webhook integration drops events intermittently",
  "Auth token refresh loop causes 429 errors",
  "ChadBot crashes on large CSV exports",
  "Memory leak when processing concurrent streams",
  "Rate limiter miscounts requests during burst traffic",
  "SSE connection drops silently after idle timeout",
  "File upload fails for attachments over 25MB",
  "Thread context lost after bot restart",
  "Unicode emoji causes parsing error in NLP pipeline",
  "Duplicate messages sent when retry logic triggers",
  "WebSocket reconnect loop on flaky connections",
  "API returns 500 when conversation exceeds 200 turns",
  "OAuth callback fails on Safari mobile",
  "Bot personality reset between sessions",
  "Search index corrupted after bulk import",
  "Markdown rendering breaks nested code blocks",
  "Timezone offset ignored in scheduled messages",
  "Hot reload breaks active conversations in dev mode",
  "gRPC deadline exceeded on multi-tenant deployments",
]

const FEATURE_TITLES = [
  "Add support for Slack thread replies",
  "Allow custom persona configuration via API",
  "Needs a dark mode for the dashboard",
  "Multi-language support for response templates",
  "Add webhook retry configuration options",
  "Support for conversation branching and forking",
  "Implement read receipts for bot messages",
  "Add batch message API endpoint",
  "Voice message transcription support",
  "Custom analytics dashboard per workspace",
  "A/B testing for response templates",
  "Priority queue for enterprise tier messages",
  "Export conversation logs to Parquet format",
  "Plugin system for third-party integrations",
  "Granular role-based access control",
  "Scheduled message delivery with timezone support",
  "Auto-tagging conversations by sentiment",
  "Streaming response mode for long-form answers",
  "Allow fine-tuning model per workspace",
  "Canary deployment support for prompt updates",
]

const COMPLAINT_TITLES = [
  "Response latency has gotten worse this week",
  "Documentation is outdated for v2 endpoints",
  "Pricing increase without feature parity",
  "Support response time is unacceptable",
  "SDK breaking changes with no migration guide",
  "Dashboard UI feels sluggish on large datasets",
  "Rate limits too aggressive for production use",
  "Onboarding wizard skips critical config steps",
  "Error messages are cryptic and unhelpful",
  "API versioning strategy is confusing",
  "Billing page shows incorrect usage metrics",
  "No changelog for minor version bumps",
  "Downtime during peak hours last Tuesday",
  "Mobile web experience is barely functional",
  "Webhook delivery order not guaranteed",
]

const PRAISE_TITLES = [
  "ChadBot handles edge cases better than competitors",
  "Great onboarding experience, setup took 5 minutes",
  "Response quality improved dramatically in v2.3",
  "Best developer documentation I've seen in AI tools",
  "Customer support resolved my issue in under an hour",
  "Context window handling is impressively smart",
  "The new streaming mode is buttery smooth",
  "Finally a chatbot that understands code context",
  "Migration from competitor took 30 minutes, flawless",
  "Enterprise SSO integration was painless",
  "Conversation threading is best-in-class",
  "The API design is incredibly intuitive",
  "Uptime has been rock solid for 6 months",
  "Love the new analytics dashboard redesign",
  "Webhook reliability is production-grade quality",
]

const TWITTER_HANDLES = [
  "@dev_sarah", "@ml_engineer_j", "@startup_cto", "@backend_beth",
  "@api_wizard", "@cloud_native_k", "@fullstack_dan", "@infra_queen",
  "@data_mike", "@sre_ops_lisa", "@devtools_fan", "@ai_builder_99",
  "@chatbot_critic", "@saas_founder", "@product_hunt_er", "@indie_hacker_z",
  "@tech_lead_amy", "@platform_eng", "@dx_advocate", "@bot_whisperer",
]

const CATEGORIES = {
  'Bug': { name: 'Bug', color: 'bg-accent-red/20 text-accent-red border-accent-red/30' },
  'Feature Request': { name: 'Feature Request', color: 'bg-accent-amber/20 text-accent-amber border-accent-amber/30' },
  'Complaint': { name: 'Complaint', color: 'bg-accent-blue/20 text-accent-blue border-accent-blue/30' },
  'Praise': { name: 'Praise', color: 'bg-accent-emerald/20 text-accent-emerald border-accent-emerald/30' },
}

const SEVERITIES = {
  'Critical': { name: 'Critical', style: 'text-red-400 font-bold' },
  'High': { name: 'High', style: 'text-orange-400 font-semibold' },
  'Medium': { name: 'Medium', style: 'text-yellow-400 font-medium' },
  'Low': { name: 'Low', style: 'text-slate-400 font-normal' },
}

const CATEGORIES_ARR = Object.values(CATEGORIES)
const SEVERITIES_ARR = Object.values(SEVERITIES)

const TIME_AGO = [
  "just now", "2 min ago", "5 min ago", "12 min ago", "28 min ago",
  "1 hour ago", "2 hours ago", "3 hours ago", "5 hours ago",
  "8 hours ago", "12 hours ago", "1 day ago", "2 days ago",
]

// ── Utility functions ────────────────────────────────────────────────────────

const pick = (arr) => arr[Math.floor(Math.random() * arr.length)]
const randInt = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min

let issueIdCounter = 100

function getTitlesForCategory(categoryName) {
  switch (categoryName) {
    case 'Bug': return BUG_TITLES
    case 'Feature Request': return FEATURE_TITLES
    case 'Complaint': return COMPLAINT_TITLES
    case 'Praise': return PRAISE_TITLES
    default: return BUG_TITLES
  }
}

function generateIssue(source) {
  const category = pick(CATEGORIES_ARR)
  const titles = getTitlesForCategory(category.name)
  const id = ++issueIdCounter

  let sourceDetail
  if (source === 'hackernews') {
    sourceDetail = `HN #${30000000 + randInt(1000000, 9999999)}`
  } else if (source === 'twitter') {
    sourceDetail = pick(TWITTER_HANDLES)
  } else {
    sourceDetail = `#${randInt(80, 450)}`
  }

  return {
    id,
    title: pick(titles),
    category,
    severity: pick(SEVERITIES_ARR),
    sourceDetail,
    timeAgo: pick(TIME_AGO),
  }
}

function apiIssueToCard(raw) {
  return {
    id: raw.id,
    title: raw.title,
    category: CATEGORIES[raw.category] || CATEGORIES['Praise'],
    severity: SEVERITIES[raw.severity] || SEVERITIES['Low'],
    sourceDetail: raw.sourceDetail,
    timeAgo: raw.timeAgo,
    url: raw.url,
  }
}

function generateBatch(source) {
  const count = randInt(3, 5)
  return Array.from({ length: count }, () => generateIssue(source))
}

// ── Components ───────────────────────────────────────────────────────────────

function SeverityDot({ severity }) {
  const dotColors = {
    Critical: 'bg-red-500',
    High: 'bg-orange-500',
    Medium: 'bg-yellow-500',
    Low: 'bg-slate-500',
  }
  return (
    <span className="flex items-center gap-1.5">
      <span className={`inline-block w-1.5 h-1.5 rounded-full ${dotColors[severity.name]}`} />
      <span className={`text-xs ${severity.style}`}>{severity.name}</span>
    </span>
  )
}

function IssueCard({ issue, index }) {
  const Wrapper = issue.url ? 'a' : 'div'
  const linkProps = issue.url ? { href: issue.url, target: '_blank', rel: 'noopener noreferrer' } : {}
  return (
    <Wrapper
      {...linkProps}
      className={`animate-fade-in-up bg-surface-700/60 backdrop-blur-sm border border-surface-500/50 rounded-lg p-3.5 hover:border-surface-400/70 hover:bg-surface-700/80 transition-all duration-200 group block ${issue.url ? 'cursor-pointer' : 'cursor-default'}`}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <h4 className="text-sm font-medium text-slate-200 leading-snug group-hover:text-white transition-colors line-clamp-2">
          {issue.title}
        </h4>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${issue.category.color}`}>
          {issue.category.name}
        </span>
        <SeverityDot severity={issue.severity} />
      </div>
      <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-surface-500/30">
        <span className="text-[11px] text-slate-500 font-mono">{issue.sourceDetail}</span>
        <span className="text-[11px] text-slate-600">{issue.timeAgo}</span>
      </div>
    </Wrapper>
  )
}

function SourceColumn({ icon, title, issues, accentColor, scanning }) {
  return (
    <div className="flex flex-col min-w-0">
      <div className="flex items-center justify-between mb-4 px-1">
        <div className="flex items-center gap-2.5">
          <span className="text-xl">{icon}</span>
          <h3 className="text-sm font-semibold text-slate-300 tracking-wide uppercase font-[family-name:var(--font-display)]">
            {title}
          </h3>
        </div>
        <span className={`text-xs font-mono font-bold px-2.5 py-1 rounded-full ${accentColor}`}>
          {issues.length}
        </span>
      </div>

      <div className="relative bg-surface-800/50 border border-surface-500/30 rounded-xl p-3 flex-1 overflow-hidden">
        {scanning && (
          <div className="absolute inset-0 z-10 pointer-events-none overflow-hidden rounded-xl">
            <div className="animate-scanline absolute inset-x-0 h-1 bg-gradient-to-r from-transparent via-accent-cyan/40 to-transparent blur-sm" />
          </div>
        )}

        <div className="space-y-2.5 max-h-[calc(100vh-260px)] overflow-y-auto pr-1">
          {issues.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-600">
              <div className="w-10 h-10 rounded-full border-2 border-dashed border-surface-500 flex items-center justify-center mb-3">
                <span className="text-lg">?</span>
              </div>
              <p className="text-xs">No issues scanned yet</p>
              <p className="text-[10px] mt-1 text-slate-700">Click "Run Scan" to begin</p>
            </div>
          ) : (
            issues.map((issue, i) => <IssueCard key={issue.id} issue={issue} index={i} />)
          )}
        </div>
      </div>
    </div>
  )
}

function SpinnerIcon() {
  return (
    <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  )
}

// ── Main Dashboard ───────────────────────────────────────────────────────────

export default function ChadBotMonitor() {
  const [hnIssues, setHnIssues] = useState([])
  const [twitterIssues, setTwitterIssues] = useState([])
  const [ghIssues, setGhIssues] = useState([])
  const [scanning, setScanning] = useState(false)
  const [scanCount, setScanCount] = useState(0)

  const runScan = useCallback(async () => {
    if (scanning) return
    setScanning(true)

    try {
      const resp = await fetch('/api/scan', { method: 'POST' })
      if (!resp.ok) throw new Error(`Scan failed: ${resp.status}`)
      const data = await resp.json()
      const r = data.results || {}

      if (r.hackernews?.length)
        setHnIssues(prev => [...r.hackernews.map(apiIssueToCard), ...prev])
      if (r.twitter?.length)
        setTwitterIssues(prev => [...r.twitter.map(apiIssueToCard), ...prev])
      if (r.github?.length)
        setGhIssues(prev => [...r.github.map(apiIssueToCard), ...prev])

      setScanCount(c => c + 1)
    } catch (err) {
      console.error('Scan error, falling back to mock data:', err)
      setHnIssues(prev => [...generateBatch('hackernews'), ...prev])
      setTwitterIssues(prev => [...generateBatch('twitter'), ...prev])
      setGhIssues(prev => [...generateBatch('github'), ...prev])
      setScanCount(c => c + 1)
    } finally {
      setScanning(false)
    }
  }, [scanning])

  const totalIssues = hnIssues.length + twitterIssues.length + ghIssues.length

  return (
    <div className="min-h-screen bg-surface-900">
      {/* Ambient background texture */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--color-surface-700)_0%,_transparent_50%)] opacity-50" />
        <div className="absolute top-0 right-0 w-96 h-96 bg-accent-cyan/[0.03] rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-accent-orange/[0.03] rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* ── Header ──────────────────────────────────────────────────── */}
        <header className="bg-surface-800/70 backdrop-blur-xl border border-surface-500/30 rounded-2xl p-4 sm:p-5 mb-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4 flex-wrap">
              {/* Logo / Brand */}
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent-cyan to-accent-orange flex items-center justify-center shadow-lg shadow-accent-cyan/20">
                  <span className="text-base font-black text-surface-900 font-[family-name:var(--font-display)]">C</span>
                </div>
                <div>
                  <h1 className="text-lg font-bold text-white tracking-tight font-[family-name:var(--font-display)]">
                    ChadBot Monitor
                  </h1>
                </div>
              </div>

              {/* Divider */}
              <div className="hidden sm:block w-px h-8 bg-surface-500/50" />

              {/* Status badges */}
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-xs text-slate-500 uppercase tracking-wider">Project</span>
                <span className="text-sm font-semibold text-slate-300 font-mono bg-surface-700/80 px-2.5 py-1 rounded-md">
                  Le Chad
                </span>

                <span className="flex items-center gap-1.5 text-xs font-medium text-accent-emerald bg-accent-emerald/10 border border-accent-emerald/20 px-2.5 py-1 rounded-full">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent-emerald animate-pulse" />
                  Active
                </span>

                <a
                  href="https://github.com/chadbot/chadbot-core"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-slate-500 hover:text-accent-cyan transition-colors font-mono flex items-center gap-1.5 bg-surface-700/50 px-2.5 py-1 rounded-md hover:bg-surface-700"
                >
                  <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                  </svg>
                  chadbot/chadbot-core
                </a>
              </div>
            </div>

            {/* Scan button + stats */}
            <div className="flex items-center gap-3">
              {totalIssues > 0 && (
                <div className="text-right hidden sm:block">
                  <span className="text-[10px] text-slate-600 uppercase tracking-widest block">Total Found</span>
                  <span className="text-xl font-bold text-white font-mono">{totalIssues}</span>
                </div>
              )}

              <button
                onClick={runScan}
                disabled={scanning}
                className={`
                  relative flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold
                  transition-all duration-300 cursor-pointer
                  ${scanning
                    ? 'bg-surface-600 text-slate-400 border border-surface-500'
                    : 'bg-gradient-to-r from-accent-cyan to-cyan-400 text-surface-900 shadow-lg shadow-accent-cyan/25 hover:shadow-accent-cyan/40 hover:scale-[1.02] active:scale-[0.98] border border-accent-cyan/50'
                  }
                `}
              >
                {scanning ? (
                  <>
                    <SpinnerIcon />
                    Scanning...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                    </svg>
                    Run Scan
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Scan progress bar */}
          {scanning && (
            <div className="mt-4 h-0.5 bg-surface-700 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-accent-cyan via-accent-orange to-accent-cyan rounded-full animate-[shimmer_1.5s_ease-in-out_infinite] bg-[length:200%_100%]"
                style={{ animation: 'shimmer 1.5s ease-in-out infinite', width: '100%' }}
              />
            </div>
          )}
        </header>

        <p className="text-sm text-slate-500 mb-8 text-center">👁️ We are monitoring channels for any issues about your project</p>

        {/* ── Source Columns ───────────────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-5">
          <SourceColumn
            icon={<span className="grayscale-0">&#x1F7E0;</span>}
            title="Hacker News"
            issues={hnIssues}
            accentColor="bg-orange-500/15 text-orange-400 border border-orange-500/25"
            scanning={scanning}
          />
          <SourceColumn
            icon={<span>&#x1F426;</span>}
            title="Twitter / X"
            issues={twitterIssues}
            accentColor="bg-sky-500/15 text-sky-400 border border-sky-500/25"
            scanning={scanning}
          />
          <SourceColumn
            icon={<span>&#x1F419;</span>}
            title="GitHub Issues"
            issues={ghIssues}
            accentColor="bg-purple-500/15 text-purple-400 border border-purple-500/25"
            scanning={scanning}
          />
        </div>

        {/* ── Footer ──────────────────────────────────────────────────── */}
        <footer className="mt-8 pb-4 text-center">
          <p className="text-[11px] text-slate-700 font-mono tracking-wider">
            CHADBOT MONITOR v1.0 &middot; {scanCount} scan{scanCount !== 1 ? 's' : ''} completed
          </p>
        </footer>
      </div>

      {/* Shimmer keyframe (inline for the progress bar) */}
      <style>{`
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  )
}
