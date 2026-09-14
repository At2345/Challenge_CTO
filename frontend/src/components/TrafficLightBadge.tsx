import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import type { TrafficLight } from "../services/api";

const STYLES: Record<TrafficLight, string> = {
  GREEN: "bg-emerald-100 text-emerald-800 border-emerald-300",
  YELLOW: "bg-amber-100 text-amber-800 border-amber-300",
  RED: "bg-rose-100 text-rose-800 border-rose-300",
};

const LABELS: Record<TrafficLight, string> = {
  GREEN: "GREEN — All checks passed",
  YELLOW: "YELLOW — Review required",
  RED: "RED — Blocked",
};

const ICONS: Record<TrafficLight, JSX.Element> = {
  GREEN: <CheckCircle2 className="w-5 h-5" />,
  YELLOW: <AlertTriangle className="w-5 h-5" />,
  RED: <XCircle className="w-5 h-5" />,
};

export default function TrafficLightBadge({ status }: { status: TrafficLight }) {
  return (
    <div
      className={`flex items-center gap-2 px-4 py-2 rounded-lg border font-semibold text-sm ${STYLES[status]}`}
    >
      {ICONS[status]}
      <span>{LABELS[status]}</span>
    </div>
  );
}
