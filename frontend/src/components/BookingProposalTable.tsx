import { Download } from "lucide-react";
import type { InvoiceRecord } from "../services/api";

export default function BookingProposalTable({ invoice }: { invoice: InvoiceRecord }) {
  const { booking_proposal, blocked } = invoice;

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(invoice, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${invoice.extracted.invoice_number || invoice.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (blocked) {
    return (
      <div className="border border-rose-200 bg-rose-50 rounded-lg p-4 text-sm text-rose-700">
        <p className="font-semibold mb-1">Automated processing blocked (RED)</p>
        <ul className="list-disc list-inside space-y-1">
          {invoice.decision_reasons.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">Double-Entry Booking Proposal (Buchungssatz)</h3>
        <button
          onClick={handleExport}
          className="flex items-center gap-1.5 text-xs font-medium text-slate-700 hover:text-slate-900 border border-gray-300 px-2 py-1 rounded-md"
        >
          <Download className="w-3.5 h-3.5" /> Export JSON
        </button>
      </div>
      {booking_proposal.length === 0 ? (
        <p className="text-xs text-gray-400">No booking proposal available yet.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
              <th className="py-1.5">Side</th>
              <th className="py-1.5">Account</th>
              <th className="py-1.5 text-right">Amount (EUR)</th>
            </tr>
          </thead>
          <tbody>
            {booking_proposal.map((line, i) => (
              <tr key={i} className="border-b border-gray-100 last:border-0">
                <td className={`py-1.5 font-medium ${line.side === "DEBIT" ? "text-slate-700" : "text-indigo-700"}`}>
                  {line.side}
                </td>
                <td className="py-1.5">
                  {line.account}
                  {line.name && <span className="text-gray-400"> · {line.name}</span>}
                </td>
                <td className="py-1.5 text-right tabular-nums">{line.amount.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
