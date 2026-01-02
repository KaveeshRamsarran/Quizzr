import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  DocumentArrowUpIcon,
  SparklesIcon,
  AcademicCapIcon,
  ChartBarIcon,
  CheckCircleIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline'

const features = [
  {
    name: 'Upload PDFs',
    description: 'Simply upload your lecture notes, slides, or textbook chapters.',
    icon: DocumentArrowUpIcon,
  },
  {
    name: 'AI Generation',
    description: 'Our AI extracts key concepts and creates flashcards & quizzes.',
    icon: SparklesIcon,
  },
  {
    name: 'Smart Study',
    description: 'Spaced repetition ensures you remember what you learn.',
    icon: AcademicCapIcon,
  },
  {
    name: 'Track Progress',
    description: 'See your improvement with detailed analytics and insights.',
    icon: ChartBarIcon,
  },
]

const benefits = [
  'AI-powered flashcard generation from any PDF',
  'Multiple question types: MCQ, True/False, Fill-in-the-blank',
  'Spaced repetition for optimal retention',
  'Source-grounded content - no hallucinations',
  'Export to Anki and other formats',
  'Works offline after initial sync',
]

export default function Landing() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 to-gray-800">
      {/* Navigation */}
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex justify-between items-center">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center">
              <span className="text-white font-bold text-xl">Q</span>
            </div>
            <span className="ml-3 text-2xl font-bold text-white">Quizzr</span>
          </div>
          <div className="flex items-center gap-4">
            <Link
              to="/login"
              className="text-gray-300 hover:text-white font-medium"
            >
              Sign in
            </Link>
            <Link
              to="/register"
              className="btn-primary"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-5xl md:text-6xl font-bold text-white tracking-tight"
          >
            Study Smarter with
            <span className="text-primary-400"> AI-Powered</span>
            <br />
            Flashcards & Quizzes
          </motion.h1>
          
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="mt-6 text-xl text-gray-300 max-w-2xl mx-auto"
          >
            Upload your PDFs and let AI create personalized study materials.
            Master any subject with spaced repetition and adaptive quizzes.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-10 flex flex-col sm:flex-row gap-4 justify-center"
          >
            <Link
              to="/register"
              className="btn-primary text-lg px-8 py-3"
            >
              Get Started
              <ArrowRightIcon className="w-5 h-5 ml-2" />
            </Link>
            <Link
              to="/login"
              className="btn bg-gray-700 text-white border border-gray-600 hover:bg-gray-600 text-lg px-8 py-3"
            >
              Watch Demo
            </Link>
          </motion.div>
        </div>

        {/* Hero image placeholder */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-16 relative"
        >
          <div className="bg-gray-800 rounded-2xl shadow-2xl border border-gray-700 p-8 max-w-4xl mx-auto">
            <div className="bg-gradient-to-br from-gray-700 to-gray-800 rounded-xl p-8 text-center border border-gray-600">
              <DocumentArrowUpIcon className="w-16 h-16 mx-auto text-primary-400 mb-4" />
              <p className="text-lg text-gray-200">
                Drop your PDF here or click to upload
              </p>
              <p className="text-sm text-gray-400 mt-2">
                Supports lecture notes, slides, textbooks up to 50MB
              </p>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <h2 className="text-3xl font-bold text-center text-white mb-12">
          How Quizzr Works
        </h2>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={feature.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              viewport={{ once: true }}
              className="text-center"
            >
              <div className="w-16 h-16 bg-primary-900/50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <feature.icon className="w-8 h-8 text-primary-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">
                {feature.name}
              </h3>
              <p className="text-gray-400">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Benefits */}
      <section className="bg-gray-900 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl font-bold text-white mb-6">
                Everything you need to ace your exams
              </h2>
              <p className="text-gray-400 text-lg mb-8">
                Quizzr uses advanced AI to understand your study materials and create
                the most effective learning experience possible.
              </p>
              
              <ul className="space-y-4">
                {benefits.map((benefit) => (
                  <li key={benefit} className="flex items-start">
                    <CheckCircleIcon className="w-6 h-6 text-primary-400 mr-3 flex-shrink-0" />
                    <span className="text-gray-300">{benefit}</span>
                  </li>
                ))}
              </ul>
            </div>
            
            <div className="bg-gray-800 rounded-2xl p-8">
              <div className="space-y-4">
                <div className="bg-gray-700 rounded-lg p-4">
                  <p className="text-primary-400 text-sm font-medium mb-2">Flashcard</p>
                  <p className="text-white font-medium">
                    What is the mitochondria?
                  </p>
                </div>
                <div className="bg-gray-700 rounded-lg p-4">
                  <p className="text-success-500 text-sm font-medium mb-2">Answer</p>
                  <p className="text-white">
                    The mitochondria is the powerhouse of the cell, responsible for
                    producing ATP through cellular respiration.
                  </p>
                </div>
                <div className="flex gap-2">
                  <button className="flex-1 py-2 rounded-lg bg-danger-500 text-white text-sm font-medium">
                    Again
                  </button>
                  <button className="flex-1 py-2 rounded-lg bg-warning-500 text-white text-sm font-medium">
                    Hard
                  </button>
                  <button className="flex-1 py-2 rounded-lg bg-success-500 text-white text-sm font-medium">
                    Good
                  </button>
                  <button className="flex-1 py-2 rounded-lg bg-primary-500 text-white text-sm font-medium">
                    Easy
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
        <h2 className="text-3xl font-bold text-white mb-4">
          Ready to study smarter?
        </h2>
        <p className="text-xl text-gray-300 mb-8">
          Join thousands of students who are acing their exams with Quizzr.
        </p>
        <Link
          to="/register"
          className="btn-primary text-lg px-8 py-3"
        >
          Get Started for Free
          <ArrowRightIcon className="w-5 h-5 ml-2" />
        </Link>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 border-t border-gray-700 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center mb-4 md:mb-0">
              <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold">Q</span>
              </div>
              <span className="ml-2 text-lg font-bold text-white">Quizzr</span>
            </div>
            <p className="text-gray-400 text-sm">
              © {new Date().getFullYear()} Quizzr. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
