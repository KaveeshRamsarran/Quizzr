import { useQuery } from '@tanstack/react-query'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import {
  FireIcon,
  AcademicCapIcon,
  ClockIcon,
  TrophyIcon,
  ChartBarIcon,
  BookOpenIcon,
} from '@heroicons/react/24/outline'
import { analyticsApi } from '../lib/api'

const COLORS = ['#8B5CF6', '#06B6D4', '#10B981', '#F59E0B', '#EF4444']

export default function Analytics() {
  const { data: overview, isLoading: isOverviewLoading } = useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: analyticsApi.getOverview,
  })

  const { data: progress, isLoading: isProgressLoading } = useQuery({
    queryKey: ['analytics', 'progress', 30],
    queryFn: () => analyticsApi.getProgress(30),
  })

  const { data: topics, isLoading: isTopicsLoading } = useQuery({
    queryKey: ['analytics', 'topics'],
    queryFn: () => analyticsApi.getTopics(),
  })

  const isLoading = isOverviewLoading || isProgressLoading || isTopicsLoading

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  if (!overview || !progress) return null

  const studyActivityData =
    progress.daily_stats?.map((item) => ({
      date: new Date(item.date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }),
      cards: item.cards,
    })) || []

  const topicMasteryData =
    topics?.topics?.map((item) => ({
      name: item.topic,
      mastery: item.accuracy,
    })) || []

  const cardStatusDistribution = [
    { name: 'New', value: overview.cards_new || 0 },
    { name: 'Learning', value: overview.cards_learning || 0 },
    { name: 'Mastered', value: overview.cards_mastered || 0 },
  ]

  const strongestTopic = topics?.topics?.length
    ? topics.topics.reduce((best, cur) => (cur.accuracy > best.accuracy ? cur : best)).topic
    : null

  const weakestTopic = topics?.topics?.length
    ? topics.topics.reduce((worst, cur) => (cur.accuracy < worst.accuracy ? cur : worst)).topic
    : null

  const bestStudyDay = progress.daily_stats?.length
    ? progress.daily_stats.reduce((best, cur) => (cur.cards > best.cards ? cur : best)).date
    : null

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Study Analytics</h1>
        <p className="text-gray-400">Track your learning progress and performance</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card bg-gray-800 border-gray-700 p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400">Current Streak</span>
            <FireIcon className="w-5 h-5 text-orange-500" />
          </div>
          <p className="text-3xl font-bold text-white">
            {overview.study_streak || 0} days
          </p>
          <p className="text-sm text-gray-400">
            Best: {overview.longest_streak || 0} days
          </p>
        </div>

        <div className="card bg-gray-800 border-gray-700 p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400">Cards Mastered</span>
            <TrophyIcon className="w-5 h-5 text-yellow-500" />
          </div>
          <p className="text-3xl font-bold text-white">
            {overview.cards_mastered || 0}
          </p>
          <p className="text-sm text-gray-400">
            of {overview.total_cards || 0} total
          </p>
        </div>

        <div className="card bg-gray-800 border-gray-700 p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400">Study Time</span>
            <ClockIcon className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-3xl font-bold text-white">
            {Math.round((overview.total_study_time_minutes || 0) / 60)}h
          </p>
          <p className="text-sm text-gray-400">total study time</p>
        </div>

        <div className="card bg-gray-800 border-gray-700 p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400">Quiz Average</span>
            <AcademicCapIcon className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-3xl font-bold text-white">
            {overview.average_quiz_score || 0}%
          </p>
          <p className="text-sm text-gray-400">
            {overview.quizzes_taken || 0} quizzes taken
          </p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Study Activity */}
        <div className="card bg-gray-800 border-gray-700 p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-semibold text-white">Study Activity</h3>
            <ChartBarIcon className="w-5 h-5 text-gray-500" />
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={studyActivityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" fontSize={12} stroke="#9CA3AF" />
                <YAxis fontSize={12} stroke="#9CA3AF" />
                <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }} labelStyle={{ color: '#F9FAFB' }} />
                <Line
                  type="monotone"
                  dataKey="cards"
                  stroke="#8B5CF6"
                  strokeWidth={2}
                  dot={{ fill: '#8B5CF6' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Topic Mastery */}
        <div className="card bg-gray-800 border-gray-700 p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-semibold text-white">Topic Mastery</h3>
            <BookOpenIcon className="w-5 h-5 text-gray-500" />
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topicMasteryData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis type="number" domain={[0, 100]} fontSize={12} stroke="#9CA3AF" />
                <YAxis dataKey="name" type="category" width={80} fontSize={12} stroke="#9CA3AF" />
                <Tooltip formatter={(value) => `${value}%`} contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }} labelStyle={{ color: '#F9FAFB' }} />
                <Bar dataKey="mastery" fill="#8B5CF6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card Status Distribution */}
        <div className="card bg-gray-800 border-gray-700 p-6">
          <h3 className="font-semibold text-white mb-6">Card Status</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={cardStatusDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={60}
                  dataKey="value"
                  label={({ name, percent }) =>
                    `${name} ${(percent * 100).toFixed(0)}%`
                  }
                >
                  {cardStatusDistribution.map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '8px' }} labelStyle={{ color: '#F9FAFB' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="card bg-gray-800 border-gray-700 p-6 lg:col-span-2">
          <h3 className="font-semibold text-white mb-4">Recent Sessions</h3>
          {overview.recent_sessions?.length > 0 ? (
            <div className="space-y-3">
              {overview.recent_sessions
                .slice(0, 5)
                .map(
                  (
                    session: {
                      date: string
                      duration_minutes: number
                      cards_studied: number
                      questions_answered: number
                      accuracy: number
                    },
                    index: number
                  ) => (
                    <div
                      key={index}
                      className="flex items-center justify-between py-2 border-b border-gray-700 last:border-0"
                    >
                      <div>
                        <p className="font-medium text-white">
                          Study session
                        </p>
                        <p className="text-sm text-gray-400">
                          {session.cards_studied} cards • {session.questions_answered} questions •{' '}
                          {Math.round(session.duration_minutes)} min
                        </p>
                      </div>
                      <span className="text-sm text-gray-400">
                        {new Date(session.date).toLocaleDateString()}
                      </span>
                    </div>
                  )
                )}
            </div>
          ) : (
            <p className="text-gray-400 text-center py-8">
              No study sessions yet. Start studying to see your progress!
            </p>
          )}
        </div>
      </div>

      {/* Performance Insights */}
      <div className="card bg-gray-800 border-gray-700 p-6">
        <h3 className="font-semibold text-white mb-4">Performance Insights</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center p-4 bg-green-900/30 rounded-lg">
            <p className="text-green-400 font-medium mb-1">Strongest Topic</p>
            <p className="text-lg text-white">
              {strongestTopic || 'N/A'}
            </p>
          </div>
          <div className="text-center p-4 bg-orange-900/30 rounded-lg">
            <p className="text-orange-400 font-medium mb-1">Needs Work</p>
            <p className="text-lg text-white">
              {weakestTopic || 'N/A'}
            </p>
          </div>
          <div className="text-center p-4 bg-blue-900/30 rounded-lg">
            <p className="text-blue-400 font-medium mb-1">Best Study Time</p>
            <p className="text-lg text-white">
              {bestStudyDay ? new Date(bestStudyDay).toLocaleDateString() : 'N/A'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
