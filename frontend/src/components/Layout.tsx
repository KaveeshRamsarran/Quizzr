import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQueryClient } from '@tanstack/react-query'
import {
  ArrowRightOnRectangleIcon, ChartBarIcon, DocumentTextIcon, HomeIcon, PlusIcon, QuestionMarkCircleIcon, RectangleStackIcon, Cog6ToothIcon,
} from '@heroicons/react/24/outline'
import { useAuthStore } from '../stores/authStore'
import { authApi } from '../lib/api'
import { Brand, Button } from './ui'
import { initials } from '../lib/format'

const NAV = [
  { to: '/dashboard', label: 'Home', icon: HomeIcon },
  { to: '/documents', label: 'Documents', icon: DocumentTextIcon },
  { to: '/decks', label: 'Flashcards', icon: RectangleStackIcon },
  { to: '/quizzes', label: 'Quizzes', icon: QuestionMarkCircleIcon },
  { to: '/analytics', label: 'Progress', icon: ChartBarIcon },
]

export default function Layout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { pathname } = useLocation()

  const signOut = async () => {
    await authApi.logout()
    logout()
    queryClient.clear()
    navigate('/')
  }

  const isActive = (to: string) => pathname === to || pathname.startsWith(`${to}/`)

  return (
    <div className="shell">
      <a href="#main" className="skip-link">Skip to content</a>

      <aside className="sidebar" aria-label="Sidebar">
        <Link to="/dashboard" aria-label="Quizzr home"><Brand /></Link>

        <Link to="/upload" className="btn btn--primary btn--block">
          <PlusIcon aria-hidden="true" />
          Upload a PDF
        </Link>

        <nav className="side-nav" aria-label="Main">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className="side-link" aria-current={isActive(to) ? 'page' : undefined}>
              {isActive(to) && <motion.span layoutId="side-active" className="side-link__bg" transition={{ type: 'spring', stiffness: 420, damping: 36 }} />}
              <Icon aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="side-foot">
          {user?.is_guest && (
            <Link to="/settings#account" className="notice notice--accent small" style={{ display: 'block' }}>
              <strong style={{ display: 'block', color: 'var(--color-ink)' }}>Guest account</strong>
              Add an email to keep your work.
            </Link>
          )}
          <NavLink to="/settings" className="side-link" aria-current={isActive('/settings') ? 'page' : undefined}>
            {isActive('/settings') && <motion.span layoutId="side-active" className="side-link__bg" transition={{ type: 'spring', stiffness: 420, damping: 36 }} />}
            <Cog6ToothIcon aria-hidden="true" />
            <span>Settings</span>
          </NavLink>
          <div className="user-chip">
            <span className="avatar">{user?.is_guest ? 'G' : initials(user?.name)}</span>
            <div className="min-w-0 flex-1">
              <div className="row-title truncate small">{user?.is_guest ? 'Guest' : user?.name}</div>
              <div className="tiny muted truncate">{user?.is_guest ? 'Not saved yet' : user?.email}</div>
            </div>
            <Button variant="ghost" size="sm" icon={<ArrowRightOnRectangleIcon />} aria-label="Sign out" title="Sign out" onClick={signOut} />
          </div>
        </div>
      </aside>

      <div className="main">
        <header className="mobile-top">
          <Link to="/dashboard" aria-label="Quizzr home"><Brand /></Link>
          <div className="flex items-center gap-1">
            <Link to="/upload" className="btn btn--primary btn--sm"><PlusIcon aria-hidden="true" /> Upload</Link>
            <Link to="/settings" className="btn btn--ghost btn--icon btn--sm" aria-label="Settings"><Cog6ToothIcon aria-hidden="true" /></Link>
          </div>
        </header>

        <main id="main" className="flex-1">
          <Outlet />
        </main>

        <nav className="bottom-nav" aria-label="Main">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} aria-current={isActive(to) ? 'page' : undefined}>
              <Icon aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  )
}
