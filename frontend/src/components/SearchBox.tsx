import { MagnifyingGlassIcon } from '@heroicons/react/24/outline'

export default function SearchBox({ id, label, value, onChange, onSubmit }: { id: string; label: string; value: string; onChange: (v: string) => void; onSubmit: () => void }) {
  return (
    <form role="search" className="search" style={{ maxWidth: 380, marginBottom: 20 }} onSubmit={(e) => { e.preventDefault(); onSubmit() }}>
      <label htmlFor={id} className="visually-hidden">{label}</label>
      <MagnifyingGlassIcon aria-hidden="true" />
      <input id={id} type="search" className="input" placeholder={label} value={value} onChange={(e) => onChange(e.target.value)} onBlur={onSubmit} />
    </form>
  )
}
