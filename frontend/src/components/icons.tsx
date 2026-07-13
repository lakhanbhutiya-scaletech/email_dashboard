// Inline 16px stroke icons (no icon lib dependency).
type P = { className?: string; size?: number }
const base = (size = 16) => ({
  width: size, height: size, viewBox: '0 0 24 24', fill: 'none',
  stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
})

export const MailIcon = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <rect x="3" y="5" width="18" height="14" rx="2" />
    <path d="m3 7 9 6 9-6" />
  </svg>
)
export const SendIcon = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" />
  </svg>
)
export const ReplyIcon = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M9 17H6a4 4 0 0 1 0-8h12" /><path d="m14 5 4 4-4 4" transform="rotate(180 15 9)" />
  </svg>
)
export const ClockIcon = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" />
  </svg>
)
export const InboxIcon = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M22 12h-6l-2 3h-4l-2-3H2" />
    <path d="M5.5 5h13L22 12v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6l3.5-7Z" />
  </svg>
)
export const UsersIcon = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </svg>
)
export const GridIcon = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" />
    <rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" />
  </svg>
)
export const BuildingIcon = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <rect x="4" y="3" width="16" height="18" rx="1.5" />
    <path d="M9 8h1M14 8h1M9 12h1M14 12h1M9 16h1M14 16h1" />
  </svg>
)
export const SearchIcon = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
  </svg>
)
export const CheckIcon = ({ className, size }: P) => (
  <svg {...base(size)} className={className}><path d="m4 12.5 5 5L20 6.5" /></svg>
)
export const AlertIcon = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M12 3 2.5 20h19L12 3Z" /><path d="M12 10v4" /><path d="M12 17.5v.01" />
  </svg>
)
export const RefreshIcon = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M21 12a9 9 0 1 1-2.64-6.36" /><path d="M21 3v6h-6" />
  </svg>
)
export const ArrowUpRight = ({ className, size }: P) => (
  <svg {...base(size)} className={className}><path d="M7 17 17 7" /><path d="M8 7h9v9" /></svg>
)
export const ArrowDownRight = ({ className, size }: P) => (
  <svg {...base(size)} className={className}><path d="m7 7 10 10" /><path d="M17 8v9H8" /></svg>
)
export const MinusIcon = ({ className, size }: P) => (
  <svg {...base(size)} className={className}><path d="M5 12h14" /></svg>
)
export const PlugIcon = ({ className, size }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M9 3v6M15 3v6" /><path d="M6 9h12l-1 5a5 5 0 0 1-10 0L6 9Z" /><path d="M12 19v2" />
  </svg>
)
