import { CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";
import type { ValidationResult } from "../services/api";

const ICONS: Record<string, JSX.Element> = {
  PASS: <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />,
  WARN: <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />,
  FAIL: <XCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />,
};

export default function ValidationResults({ validations }: { validations: ValidationResult[] }) {
  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
        <Info className="w-4 h-4" /> Audit Trail (R0–R8)
      </h3>
      <ul className="space-y-2">
        {validations.map((v, i) => (
          <li key={i} className="flex items-start gap-2 text-sm">
            {ICONS[v.status] || <Info className="w-4 h-4 text-gray-400 flex-shrink-0" />}
            <div>
              <span className="font-medium text-gray-800">{v.check}</span>
              <p className="text-gray-500 text-xs mt-0.5">{v.details}</p>
            </div>
          </li>
        ))}
        {validations.length === 0 && <li className="text-xs text-gray-400">No validations recorded yet.</li>}
      </ul>
    </div>
  );
}
