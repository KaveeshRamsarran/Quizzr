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
  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analytics'],
    queryFn: analyticsApi.get,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  if (!analytics) return null

  const studyActivityData =
    analytics.study_activity?.map((item: { date: string; cards_studied: number }) => ({
      date: new Date(item.date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }),
      cards: item.cards_studied,
    })) || []

  const topicMasteryData =
    analytics.topic_mastery?.map(
      (item: { tag_name: string; mastery_percentage: number }) => ({
        name: item.tag_name,
        mastery: item.mastery_percentage,
      })
    ) || []

  const difficultyDistribution = [
    { name: 'Easy', value: analytics.card_difficulty?.easy || 0 },
    { name: 'Medium', value: analytics.card_difficulty?.medium || 0 },
    { name: 'Hard', value: analytics.card_difficulty?.hard || 0 },
  ]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Study Analytics</h1>
        <p className="text-gray-600">Track your learning progress and performance</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-500">Current Streak</span>
            <FireIcon className="w-5 h-5 text-orange-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {analytics.streak?.current || 0} days
          </p>
          <p className="text-sm text-gray-500">
            Best: {analytics.streak?.longest || 0} days
          </p>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-500">Cards Mastered</span>
            <TrophyIcon className="w-5 h-5 text-yellow-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {analytics.cards_mastered || 0}
          </p>
          <p className="text-sm text-gray-500">
            of {analytics.total_cards || 0} total
          </p>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-500">Study Time</span>
            <ClockIcon className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {Math.round((analytics.total_study_time || 0) / 60)}h
          </p>
          <p className="text-sm text-gray-500">total study time</p>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-500">Quiz Average</span>
            <AcademicCapIcon className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {analytics.quiz_average || 0}%
          </p>
          <p className="text-sm text-gray-500">
            {analytics.quizzes_taken || 0} quizzes taken
          </p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Study Activity */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-semibold text-gray-900">Study Activity</h3>
            <ChartBarIcon className="w-5 h-5 text-gray-400" />
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={studyActivityData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip />
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
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-semibold text-gray-900">Topic Mastery</h3>
            <BookOpenIcon className="w-5 h-5 text-gray-400" />
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topicMasteryData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 100]} fontSize={12} />
                <YAxis dataKey="name" type="category" width={80} fontSize={12} />
                <Tooltip formatter={(value) => `${value}%`} />
                <Bar dataKey="mastery" fill="#8B5CF6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card Difficulty Distribution */}
        <div className="card p-6">
          <h3 className="font-semibold text-gray-900 mb-6">Card Difficulty</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={difficultyDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={60}
                  dataKey="value"
                  label={({ name, percent }) =>
                    `${name} ${(percent * 100).toFixed(0)}%`
                  }
                >
                  {difficultyDistribution.map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="card p-6 lg:col-span-2">
          <h3 className="font-semibold text-gray-900 mb-4">Recent Sessions</h3>
          {analytics.recent_sessions?.length > 0 ? (
            <div className="space-y-3">
              {analytics.recent_sessions
                .slice(0, 5)
                .map(
                  (
                    session: {
                      id: number
                      deck_name: string
                      cards_studied: number
                      duration: number
                      date: string
                    },
                    index: number
                  ) => (
                    <div
                      key={index}
                      className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
                    >
                      <div>
                        <p className="font-medium text-gray-900">
                          {session.deck_name}
                        </p>
                        <p className="text-sm text-gray-500">
                          {session.cards_studied} cards •{' '}
                          {Math.round(session.duration / 60)} min
                        </p>
                      </div>
                      <span className="text-sm text-gray-500">
                        {new Date(session.date).toLocaleDateString()}
                      </span>
                    </div>
                  )
                )}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">
              No study sessions yet. Start studying to see your progress!
            </p>
          )}
        </div>
      </div>

      {/* Performance Insights */}
      <div className="card p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Performance Insights</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <p className="text-green-600 font-medium mb-1">Strongest Topic</p>
            <p className="text-lg text-gray-900">
              {analytics.strongest_topic || 'N/A'}
            </p>
          </div>
          <div className="text-center p-4 bg-orange-50 rounded-lg">
            <p className="text-orange-600 font-medium mb-1">Needs Work</p>
            <p className="text-lg text-gray-900">
              {analytics.weakest_topic || 'N/A'}
            </p>
          </div>
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <p className="text-blue-600 font-medium mb-1">Best Study Time</p>
            <p className="text-lg text-gray-900">
              {analytics.best_study_time || 'N/A'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
