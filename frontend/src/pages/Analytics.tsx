import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { BoltIcon, ChartBarIcon, ClockIcon, FireIcon, TrophyIcon } from '@heroicons/react/24/outline'
import { analyticsApi, errorMessage } from '../lib/api'
import { EmptyState, ErrorState, PageHeader, SectionTitle, Segmented, SkeletonRows } from '../components/ui'
import { CountUp, Item, Page, ProgressBar, Stagger } from '../components/motion'
import type { DailyStat } from '../types'

type Range = '7' | '30' | '90'

function ChartTooltip({ active, payload }: { active?: boolean; payload?: { payload: DailyStat }[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="card" style={{ padding: '10px 14px', fontSize: 'var(--text-sm)', boxShadow: 'var(--shadow-lift)' }}>
      <div className="row-title">{new Date(d.date + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' })}</div>
      <div className="muted">{d.cards} cards, {d.questions} questions</div>
      {d.items > 0 && <div className="muted">{Math.round(d.accuracy)}% right, {Math.round(d.minutes)} min</div>}
    </div>
  )
}

export default function Analytics() {
  const [params, setParams] = useSearchParams()
  const range = (['7', '30', '90'].includes(params.get('days') ?? '') ? params.get('days') : '30') as Range

  const overview = useQuery({ queryKey: ['analytics', 'overview'], queryFn: analyticsApi.getOverview })
  const progress = useQuery({ queryKey: ['analytics', 'progress', range], queryFn: () => analyticsApi.getProgress(Number(range)) })
  const topics = useQuery({ queryKey: ['analytics', 'topics'], queryFn: analyticsApi.getTopics })
  const missed = useQuery({ queryKey: ['analytics', 'missed'], queryFn: () => analyticsApi.getMissed(8) })

  const o = overview.data
  const p = progress.data
  const hasActivity = !!p?.daily_stats.some((d) => d.items > 0)

  return (
    <Page>
      <PageHeader
        title="Progress"
        sub="How your studying is going"
        actions={
          <Segmented<Range>
            label="Time range"
            value={range}
            onChange={(v) => setParams(v === '30' ? {} : { days: v }, { replace: true })}
            options={[{ value: '7', label: '7 days' }, { value: '30', label: '30 days' }, { value: '90', label: '90 days' }]}
          />
        }
      />

      {overview.isError ? <ErrorState message={errorMessage(overview.error)} onRetry={() => overview.refetch()} /> : (
        <Stagger className="stats">
          {[
            { label: 'Current streak', icon: FireIcon, value: o?.study_streak, unit: o?.study_streak === 1 ? 'day' : 'days' },
            { label: 'Longest streak', icon: TrophyIcon, value: o?.longest_streak, unit: o?.longest_streak === 1 ? 'day' : 'days' },
            { label: 'Time studied', icon: ClockIcon, value: o?.total_study_time_minutes, unit: 'min' },
            { label: 'Answered right', icon: BoltIcon, value: o ? Math.round(o.overall_accuracy) : undefined, unit: '%' },
          ].map((s) => (
            <Item key={s.label} className="card stat">
              <div className="stat__top"><span>{s.label}</span><s.icon aria-hidden="true" /></div>
              <div className="stat__value">{s.value == null ? '–' : <CountUp value={s.value} />}<small>{s.unit}</small></div>
            </Item>
          ))}
        </Stagger>
      )}

      <section className="section" aria-labelledby="activity-title">
        <SectionTitle
          title={<span id="activity-title">Daily activity</span>}
          action={p && hasActivity ? <span className="small muted">{p.this_week_vs_last.this_week_items} items this week</span> : undefined}
        />
        {progress.isLoading ? <div className="skeleton" style={{ height: 320, borderRadius: 18 }} /> : progress.isError ? (
          <ErrorState message={errorMessage(progress.error)} onRetry={() => progress.refetch()} />
        ) : !hasActivity ? (
          <div className="card"><EmptyState icon={<ChartBarIcon />} title="No activity yet">Study a deck or take a quiz and your daily totals show up here.</EmptyState></div>
        ) : (
          <div className="card" style={{ padding: '20px 12px 12px' }}>
            <div style={{ width: '100%', height: 300 }} role="img" aria-label={`Cards and questions studied per day over the last ${range} days`}>
              <ResponsiveContainer>
                <AreaChart data={p!.daily_stats} margin={{ top: 8, right: 12, bottom: 0, left: -16 }}>
                  <CartesianGrid stroke="var(--color-rule)" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(v: string) => new Date(v + 'T00:00:00').toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}
                    tick={{ fill: 'var(--color-muted)', fontSize: 12, fontFamily: 'var(--font-display)' }}
                    axisLine={false}
                    tickLine={false}
                    minTickGap={28}
                  />
                  <YAxis allowDecimals={false} tick={{ fill: 'var(--color-muted)', fontSize: 12, fontFamily: 'var(--font-display)' }} axisLine={false} tickLine={false} width={44} />
                  <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'var(--color-rule-2)', strokeDasharray: '4 4' }} />
                  <Area type="monotone" dataKey="items" stroke="var(--color-accent)" strokeWidth={2.5} fill="var(--color-accent-soft)" fillOpacity={0.6} animationDuration={900} dot={false} activeDot={{ r: 5, fill: 'var(--color-accent)', stroke: 'var(--color-surface)', strokeWidth: 2 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <p className="small muted" style={{ padding: '4px 12px 0' }}>Daily goal {p!.daily_goal} cards, reached on {Math.round((p!.goal_completion_rate / 100) * 7)} of the last 7 days.</p>
          </div>
        )}
      </section>

      <div className="grid gap-x-8 lg:grid-cols-2">
        <section className="section" aria-labelledby="mastery-title">
          <SectionTitle title={<span id="mastery-title">Card mastery</span>} />
          {o ? (
            o.total_cards === 0 ? <div className="card card--soft" style={{ padding: 18 }}><p className="small muted">No cards yet.</p></div> : (
              <div className="card card--pad grid gap-5">
                {([
                  ['Mastered', o.cards_mastered, 'Seen again in three weeks or more'],
                  ['Learning', o.cards_learning, 'Studied and coming back soon'],
                  ['Not studied yet', o.cards_new, 'Waiting in a deck'],
                ] as const).map(([label, n, hint]) => (
                  <div key={label}>
                    <div className="flex items-baseline justify-between gap-3" style={{ marginBottom: 8 }}>
                      <div><span className="row-title">{label}</span> <span className="small muted">{hint}</span></div>
                      <span className="figure-font" style={{ color: 'var(--color-ink)', fontSize: '1.15rem' }}>{n}</span>
                    </div>
                    <ProgressBar value={(n / o.total_cards) * 100} label={`${label} share`} />
                  </div>
                ))}
              </div>
            )
          ) : <SkeletonRows rows={1} height={180} />}
        </section>

        <section className="section" aria-labelledby="topics-title">
          <SectionTitle title={<span id="topics-title">Quiz topics</span>} action={<span className="small muted">Weakest first</span>} />
          {topics.isLoading ? <SkeletonRows rows={1} height={180} /> : !topics.data?.topics.length ? (
            <div className="card card--soft" style={{ padding: 18 }}><p className="small muted">Take a quiz to see how you do on each topic.</p></div>
          ) : (
            <div className="card card--pad grid gap-5">
              {topics.data.topics.slice(0, 6).map((t) => (
                <div key={t.topic}>
                  <div className="flex items-baseline justify-between gap-3" style={{ marginBottom: 8 }}>
                    <span className="row-title truncate">{t.topic}</span>
                    <span className="figure-font small" style={{ color: t.accuracy < 70 ? 'var(--color-error)' : 'var(--color-ink)' }}>{Math.round(t.accuracy)}%</span>
                  </div>
                  <ProgressBar value={t.accuracy} label={`${t.topic} accuracy`} />
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <section className="section" aria-labelledby="missed-title">
        <SectionTitle title={<span id="missed-title">Questions to revisit</span>} />
        {missed.isLoading ? <SkeletonRows rows={2} /> : !missed.data?.questions.length ? (
          <div className="card card--soft" style={{ padding: 18 }}><p className="small muted">Questions you get wrong show up here so you can go back to them.</p></div>
        ) : (
          <Stagger className="card list">
            {missed.data.questions.map((q) => (
              <Item key={q.question_id} className="list-row">
                <div className="flex-1 min-w-0">
                  <p className="row-title">{q.question_text}</p>
                  <p className="row-meta">{q.source_document}</p>
                </div>
                <span className="badge badge--error">Missed {q.times_incorrect}×</span>
              </Item>
            ))}
          </Stagger>
        )}
      </section>
    </Page>
  )
}
