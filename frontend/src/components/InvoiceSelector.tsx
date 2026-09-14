import { useMemo, useRef } from "react";
import { Upload, FileText } from "lucide-react";
import type { InvoiceRecord } from "../services/api";

const DOT_COLOR: Record<string, string> = {
  GREEN: "bg-emerald-500",
  YELLOW: "bg-amber-500",
  RED: "bg-rose-500",
};

interface Props {
  invoices: InvoiceRecord[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onUpload: (file: File) => void;
  uploading: boolean;
}

export default function InvoiceSelector({ invoices, selectedId, onSelect, onUpload, uploading }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  // Show every processed invoice from this session, in upload order, each
  // labeled with a purely sequential, content-agnostic identifier
  // (Rechnung-00001, Rechnung-00002, ...) rather than any value pulled from
  // the document itself (invoice number, filename, vendor, etc.).
  const displayInvoices = useMemo(() => {
    return [...invoices].sort(
      (x, y) => new Date(x.audit?.processed_at || 0).getTime() - new Date(y.audit?.processed_at || 0).getTime()
    );
  }, [invoices]);

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-gray-200">
        <button
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="w-full flex items-center justify-center gap-2 bg-slate-900 text-white text-sm font-medium py-2 rounded-md hover:bg-slate-700 disabled:opacity-50"
        >
          <Upload className="w-4 h-4" />
          {uploading ? "Uploading..." : "Upload Invoice PDF"}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onUpload(file);
            e.target.value = "";
          }}
        />
      </div>
      <div className="flex-1 overflow-y-auto">
        {displayInvoices.length === 0 && (
          <p className="text-sm text-gray-400 p-4 text-center">No invoices processed yet.</p>
        )}
        {displayInvoices.map((inv, index) => (
          <button
            key={inv.id}
            onClick={() => onSelect(inv.id)}
            className={`w-full flex items-center gap-2 px-3 py-2 text-left text-sm border-b border-gray-100 hover:bg-slate-50 ${
              selectedId === inv.id ? "bg-slate-100" : ""
            }`}
          >
            <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${DOT_COLOR[inv.traffic_light]}`} />
            <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <span className="truncate">{`Rechnung-${String(index + 1).padStart(5, "0")}`}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
