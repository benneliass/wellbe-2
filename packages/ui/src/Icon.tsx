import {
  Activity,
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  BarChart3,
  Bell,
  Book,
  Calendar,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  CircleHelp,
  CircleUser,
  ClipboardList,
  Clock,
  Eye,
  FileSearch,
  FileText,
  Filter,
  FlaskConical,
  GitFork,
  Globe,
  HeartPulse,
  HelpCircle,
  Home,
  LineChart,
  List,
  Lock,
  type LucideIcon,
  MessageCircle,
  Pause,
  Pencil,
  Plus,
  PlusCircle,
  Search,
  Settings,
  Share,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  TrendingUp,
  User,
  Users,
  X,
} from "lucide-react";

/**
 * Single icon registry for the whole app. We map the design system's kebab-case
 * icon names (used throughout the data/meta maps) to lucide-react components.
 * Pinned to lucide 0.453 to match the names the design system validated against.
 *
 * To add an icon: import it above and add one line to REGISTRY.
 */
const REGISTRY: Record<string, LucideIcon> = {
  activity: Activity,
  "alert-circle": AlertCircle,
  "arrow-left": ArrowLeft,
  "arrow-right": ArrowRight,
  "badge-check": BadgeCheck,
  "bar-chart-3": BarChart3,
  bell: Bell,
  book: Book,
  calendar: Calendar,
  check: Check,
  "check-circle-2": CheckCircle2,
  "chevron-down": ChevronDown,
  "chevron-right": ChevronRight,
  "circle-help": CircleHelp,
  "circle-user": CircleUser,
  "clipboard-list": ClipboardList,
  clock: Clock,
  eye: Eye,
  "file-search": FileSearch,
  "file-text": FileText,
  filter: Filter,
  "flask-conical": FlaskConical,
  "git-fork": GitFork,
  globe: Globe,
  "heart-pulse": HeartPulse,
  "help-circle": HelpCircle,
  home: Home,
  "line-chart": LineChart,
  list: List,
  lock: Lock,
  "message-circle": MessageCircle,
  pause: Pause,
  pencil: Pencil,
  plus: Plus,
  "plus-circle": PlusCircle,
  search: Search,
  settings: Settings,
  share: Share,
  "shield-check": ShieldCheck,
  "sliders-horizontal": SlidersHorizontal,
  sparkles: Sparkles,
  "trending-up": TrendingUp,
  user: User,
  users: Users,
  x: X,
};

export type IconName = keyof typeof REGISTRY;

export interface IconProps {
  /** Kebab-case lucide name, e.g. "flask-conical". */
  name: string;
  size?: number;
  strokeWidth?: number;
  className?: string;
}

export function Icon({ name, size = 18, strokeWidth = 1.75, className }: IconProps) {
  const Glyph = REGISTRY[name] ?? Circle;
  return (
    <Glyph
      size={size}
      strokeWidth={strokeWidth}
      className={className}
      aria-hidden="true"
      focusable="false"
    />
  );
}
