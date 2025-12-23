// User types
export interface User {
  id: number
  email: string
  name: string
  school: string | null
  timezone: string
  preferred_difficulty: number
  study_goal_days: number | null
  simple_mode: boolean
  role: 'standard' | 'admin' | 'guest'
  is_verified: boolean
  study_streak: number
  total_study_time_minutes: number
  created_at: string
  last_login: string | null
}

export interface UserPreferences {
  theme?: 'light' | 'dark' | 'system'
  cards_per_session?: number
  quiz_question_count?: number
  show_hints?: boolean
  daily_goal?: number
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

// Document types
export interface Document {
  id: number
  filename: string
  original_filename: string
  title: string | null
  description: string | null
  file_size: number
  mime_type: string
  status: 'pending' | 'processing' | 'processed' | 'error'
  page_count: number | null
  error_message: string | null
  course_id: number | null
  created_at: string
  updated_at: string
}

export interface DocumentListResponse {
  documents: Document[]
  total: number
  page: number
  limit: number
  pages: number
}

// Deck types
export interface Deck {
  id: number
  title: string
  description: string | null
  card_count: number
  mastered_count: number
  document_id: number | null
  course_id: number | null
  is_public: boolean
  created_at: string
  updated_at: string
}

export interface Card {
  id: number
  front: string
  back: string
  card_type: 'basic' | 'cloze' | 'reverse' | 'image'
  difficulty: number
  source_snippets: string[]
  source_page: number | null
  needs_review: boolean
  review_reason: string | null
  created_at: string
}

export interface DeckDetail extends Deck {
  cards: Card[]
}

export interface DeckListResponse {
  decks: Deck[]
  total: number
  page: number
  limit: number
  pages: number
}

// Quiz types
export interface Quiz {
  id: number
  title: string
  description: string | null
  question_count: number
  time_limit_minutes: number | null
  pass_percentage: number
  attempts_count: number
  best_score: number | null
  document_id: number | null
  course_id: number | null
  created_at: string
  updated_at: string
}

export interface QuizQuestion {
  id: number
  question_type: 'multiple_choice' | 'true_false' | 'fill_blank' | 'short_answer'
  question_text: string
  options: string[] | null
  correct_answer: string
  explanation: string | null
  difficulty: number
  source_snippets: string[]
  source_page: number | null
}

export interface QuizDetail extends Quiz {
  questions: QuizQuestion[]
}

export interface QuizListResponse {
  quizzes: Quiz[]
  total: number
  page: number
  limit: number
  pages: number
}

export interface QuizAttempt {
  id: number
  quiz_id: number
  score: number | null
  percentage: number | null
  correct_count: number
  total_questions: number
  time_spent_seconds: number | null
  started_at: string
  completed_at: string | null
}

export interface AttemptResult {
  attempt_id: number
  score: number
  percentage: number
  correct_count: number
  total_questions: number
  passed: boolean
  time_spent_seconds: number
  question_results: QuestionResult[]
}

export interface QuestionResult {
  question_id: number
  is_correct: boolean
  given_answer: string
  correct_answer: string
  explanation: string | null
}

// Generation types
export interface GenerationJob {
  job_id: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  message: string | null
  progress: number | null
  result_id: number | null
  created_at: string
  completed_at: string | null
}

export interface DeckGenerationRequest {
  document_id: number
  title?: string
  card_count?: number
  card_types?: ('basic' | 'cloze' | 'reverse')[]
  difficulty?: 'easy' | 'medium' | 'hard' | 'mixed'
  focus_topics?: string[]
}

export interface QuizGenerationRequest {
  document_id: number
  title?: string
  question_count?: number
  question_types?: ('multiple_choice' | 'true_false' | 'fill_blank' | 'short_answer')[]
  difficulty?: 'easy' | 'medium' | 'hard' | 'mixed'
  focus_topics?: string[]
}

// Analytics types
export interface AnalyticsOverview {
  total_documents: number
  total_decks: number
  total_quizzes: number
  total_cards_studied: number
  total_quizzes_taken: number
  cards_mastered: number
  average_quiz_score: number
  study_streak: number
  cards_due_today: number
}

export interface TopicAnalytics {
  topic: string
  card_count: number
  mastery_percentage: number
  quiz_accuracy: number
  study_time_minutes: number
}

export interface StudyProgress {
  date: string
  cards_studied: number
  quizzes_taken: number
  accuracy: number
}

export interface StudyProgressResponse {
  daily_progress: StudyProgress[]
  total_cards_studied: number
  total_quizzes_taken: number
  average_accuracy: number
}

// Spaced repetition types
export interface CardReview {
  rating: 'again' | 'hard' | 'good' | 'easy'
  time_spent_ms: number
}

export interface CardReviewResponse {
  card_id: number
  next_review_at: string
  interval_days: number
  ease_factor: number
}
