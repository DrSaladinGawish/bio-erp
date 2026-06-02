interface IconProps {
  size?: number;
  className?: string;
}

export function BrainIcon({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 2a10 10 0 0 1 7 17" />
      <path d="M12 2a10 10 0 0 0-7 17" />
      <circle cx="12" cy="12" r="3" />
      <path d="M12 9v6M9 12h6" />
      <path d="M4 4l3 3M20 4l-3 3M4 20l3-3M20 20l-3-3" />
    </svg>
  );
}

export function HeartIcon({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
      <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
      <circle cx="12" cy="11" r="2" fill="currentColor" />
    </svg>
  );
}

export function DnaIcon({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
      <path d="M8 3h8M8 21h8" />
      <path d="M6 6c4 2 4 10 0 12" />
      <path d="M18 6c-4 2-4 10 0 12" />
      <path d="M12 6v2M12 16v2" />
      <circle cx="12" cy="9" r="1" fill="currentColor" />
      <circle cx="12" cy="15" r="1" fill="currentColor" />
    </svg>
  );
}

export function CellIcon({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="2" fill="currentColor" />
      <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
    </svg>
  );
}

export function OrganIcon({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
      <path d="M12 4C8 4 4 7 4 12s4 8 8 8 8-3 8-8-4-8-8-8z" />
      <path d="M12 8v4l3 3" />
      <circle cx="12" cy="12" r="2" fill="currentColor" />
    </svg>
  );
}

export function ReportIcon({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
      <rect x="4" y="2" width="16" height="20" rx="2" />
      <path d="M8 7h8M8 11h8M8 15h5" />
      <circle cx="16" cy="17" r="3" fill="none" />
      <path d="M16 15v2l1 1" />
    </svg>
  );
}

export function MoneyIcon({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v12M8 10h6a2 2 0 0 1 0 4H8" />
    </svg>
  );
}

export function PulseIcon({ size = 24, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className}>
      <polyline points="2 14 7 14 9 10 12 18 14 8 17 14 22 14" />
    </svg>
  );
}
