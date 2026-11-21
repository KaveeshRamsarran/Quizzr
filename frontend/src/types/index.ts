// Shapes returned by the Quizzr API (backend/app/schemas).

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
  is_guest: boolean
  is_verified: boolean
  study_streak: number
  total_study_time_minutes: number
  created_at: string
  last_login: string | null
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export type DocumentStatus = 'pending' | 'processing' | 'processed' | 'error'

export interface Document {
  id: number
  filename: string
  original_filename: string
  title: string | null
  description: string | null
  file_size: number
  mime_type: string
  status: DocumentStatus
  style: string
  page_count: number
  processing_error: string | null
  error_message: string | null
  ocr_used: boolean
  course_id: number | null
  created_at: string
  updated_at: string
  processed_at: string | null
}

export interface DocumentPage {
  id: number
  page_number: number
  text_content: string | null
  text_length: number
  used_ocr: boolean
  headings_on_page: string[] | null
}

export interface Chunk {
  id: number
  chunk_index: number
  start_page: number
  end_page: number
  content: string
  content_length: number
  heading_context: string | null
  key_terms: string[] | null
  content_type: string
}

export interface DocumentDetail extends Document {
  pages: DocumentPage[]
  chunks: Chunk[]
}

export interface Paginated {
  total: number
  page: number
  limit: number
  pages: number
}

export interface DocumentListResponse extends Paginated {
  documents: Document[]
}

export interface Deck {
  id: number
  name: string
  title: string
  description: string | null
  deck_type: string
  card_count: number
  mastered_count: number
  due_count: number
  new_count: number
  source_document_id: number | null
  document_id: number | null
  course_id: number | null
  is_public: boolean
  color: string
  created_at: string
  updated_at: string
  last_studied: string | null
}

export interface Card {
  id: number
  deck_id: number
  card_type: string
  front: string
  back: string
  extra_explanation: string | null
  example: string | null
  mnemonic: string | null
  cloze_text: string | null
  cloze_answer: string | null
  difficulty: number
  needs_review: boolean
  review_reason: string | null
  source_pages: number[] | null
  source_snippets: string[] | null
  times_studied: number
  times_correct: number
  times_incorrect: number
  is_suspended: boolean
  is_mastered: boolean
  accuracy: number
  created_at: string
  last_studied: string | null
}

export interface DeckDetail extends Deck {
  cards: Card[]
}

export interface DeckListResponse extends Paginated {
  decks: Deck[]
}

export interface Quiz {
  id: number
  name: string
  title: string
  description: string | null
  difficulty: string
  question_count: number
  time_limit_minutes: number | null
  pass_percentage: number
  shuffle_questions: boolean
  shuffle_options: boolean
  show_explanations: boolean
  question_types: string[] | null
  times_taken: number
  attempts_count: number
  average_score: number | null
  best_score: number | null
  source_document_id: number | null
  document_id: number | null
  created_at: string
  updated_at: string
}

export interface QuizOption {
  id: string
  text: string
}

export type QuestionType = 'mcq' | 'multi_select' | 'true_false' | 'short_answer' | 'fill_blank' | 'matching'

export interface QuizQuestion {
  id: number
  quiz_id: number
  question_type: QuestionType
  question_text: string
  options: QuizOption[] | null
  correct_answer: string | null
  explanation: string | null
  difficulty: number
  points: number
  topic: string | null
  question_order: number
  source_pages: number[] | null
  source_snippets: string[] | null
  needs_review: boolean
}

export interface QuizDetail extends Quiz {
  questions: QuizQuestion[]
}

export interface QuizListResponse extends Paginated {
  quizzes: Quiz[]
}

export interface QuizAttempt {
  id: number
  quiz_id: number
  is_completed: boolean
  score: number | null
  points_earned: number
  points_possible: number
  correct_count: number
  incorrect_count: number
  time_started: string
  time_completed: string | null
  time_spent_seconds: number | null
}

export interface AnswerResult {
  is_correct: boolean
  correct_answer: string | null
  explanation: string | null
}

export interface QuestionReview {
  question_id: number
  question_text: string
  question_type: QuestionType
  options: QuizOption[] | null
  correct_answer: string
  user_answer: string | null
  is_correct: boolean
  explanation: string | null
  topic: string | null
}

export interface AttemptResult {
  attempt_id: number
  quiz_id: number
  quiz_name: string
  score: number
  percentage: number
  passed: boolean
  points_earned: number
  points_possible: number
  correct_count: number
  incorrect_count: number
  time_spent_seconds: number
  by_topic: Record<string, { correct: number; total: number }>
  by_type: Record<string, { correct: number; total: number }>
  weak_topics: string[]
  questions: QuestionReview[]
}

export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface GenerationJob {
  job_id: number
  job_type: 'deck_generation' | 'quiz_generation' | null
  status: JobStatus
  message: string | null
  step: string | null
  progress: number | null
  result_id: number | null
  document_id: number | null
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
  time_limit_minutes?: number | null
  focus_topics?: string[]
}

export interface StudySession {
  date: string
  duration_minutes: number
  cards_studied: number
  questions_answered: number
  accuracy: number
}

export interface AnalyticsOverview {
  study_streak: number
  longest_streak: number
  total_study_time_minutes: number
  avg_daily_study_minutes: number
  total_documents: number
  total_decks: number
  total_cards: number
  total_quizzes: number
  cards_mastered: number
  cards_learning: number
  cards_new: number
  mastery_rate: number
  overall_accuracy: number
  cards_studied_today: number
  cards_due_today: number
  reviews_due_today: number
  quizzes_taken: number
  average_quiz_score: number
  last_study_date: string | null
  recent_sessions: StudySession[]
}

export interface DailyStat {
  date: string
  cards: number
  questions: number
  minutes: number
  accuracy: number
  items: number
}

export interface StudyProgress {
  period: string
  daily_stats: DailyStat[]
  accuracy_trend: number[]
  volume_trend: number[]
  this_week_vs_last: { cards: number; accuracy: number; time: number; this_week_items: number; this_week_minutes: number }
  daily_goal: number
  goal_completion_rate: number
}

export interface TopicPerformance {
  topic: string
  total_items: number
  correct: number
  incorrect: number
  accuracy: number
  last_studied: string | null
}

export interface TopicAnalytics {
  topics: TopicPerformance[]
  weak_topics: string[]
  strong_topics: string[]
  recommended_review: string[]
}

export interface MissedQuestion {
  question_id: number
  question_text: string
  question_type: string
  times_incorrect: number
  times_correct: number
  accuracy: number
  topic: string | null
  source_document: string | null
}

export interface Suggestion {
  type: string
  priority: 'high' | 'medium' | 'low'
  title: string
  description: string
  action: string
  target_id: number | null
}


export interface CardReviewResponse {
  card_id: number
  next_review: string
  interval_days: number
  easiness: number
  repetitions: number
}
