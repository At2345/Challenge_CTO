import { useEffect, useState } from "react";
import { Save } from "lucide-react";
import type { ExtractedFields } from "../services/api";

interface Props {
  extracted: ExtractedFields;
  editable: boolean;
  submitting: boolean;
  onSubmit: (updated: Partial<ExtractedFields>) => void;
}

const FIELD_LABELS: { key: keyof ExtractedFields; label: string; type: "text" | "date" | "number" }[] = [
  { key: "invoice_recipient", label: "Invoice Recipient", type: "text" },
  { key: "vendor_name", label: "Vendor / Supplier", type: "text" },
  { key: "invoice_number", label: "Invoice Number", type: "text" },
  { key: "invoice_date", label: "Invoice Date", type: "date" },
  { key: "service_date", label: "Service Date (Leistungsdatum)", type: "date" },
  { key: "currency", label: "Currency", type: "text" },
  { key: "net_amount", label: "Net Amount", type: "number" },
  { key: "vat_rate", label: "VAT Rate (%)", type: "number" },
  { key: "vat_amount", label: "VAT Amount", type: "number" },
  { key: "gross_amount", label: "Gross Amount", type: "number" },
  { key: "description", label: "Service Description", type: "text" },
];

export default function ExtractedDataForm({ extracted, editable, submitting, onSubmit }: Props) {
  const [values, setValues] = useState<ExtractedFields>(extracted);

  useEffect(() => {
    const computedDesc = extracted.description && extracted.description.trim().length > 0
      ? extracted.description
      : `${extracted.vendor_name ?? ""}${extracted.vendor_name ? " " : ""}Rechnung`;
    setValues({ ...extracted, description: computedDesc });
  }, [extracted]);

  const handleChange = (key: keyof ExtractedFields, raw: string, type: string) => {
    setValues((prev) => ({
      ...prev,
      [key]: type === "number" ? (raw === "" ? null : Number(raw)) : raw,
    }));
  };

  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">Extracted Invoice Data</h3>
      <p className="text-xs text-gray-500 mb-3">{values.vendor_name || "Unbekannter Kreditor"} · Rechnung</p>
      <div className="grid grid-cols-2 gap-3">
        {FIELD_LABELS.map(({ key, label, type }) => (
          <div key={key} className={key === "description" ? "col-span-2" : ""}>
            <label className="block text-xs text-gray-500 mb-1">{label}</label>
            <input
              type={type}
              value={(values[key] as any) ?? ""}
              disabled={!editable}
              onChange={(e) => handleChange(key, e.target.value, type)}
              className={`w-full text-sm px-2 py-1.5 border rounded-md ${
                editable ? "border-gray-300 bg-white" : "border-gray-100 bg-gray-50 text-gray-500"
              }`}
            />
          </div>
        ))}
      </div>
      {editable && (
        <button
          onClick={() => onSubmit(values)}
          disabled={submitting}
          className="mt-4 flex items-center gap-2 bg-amber-600 text-white text-sm font-medium px-4 py-2 rounded-md hover:bg-amber-700 disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {submitting ? "Revalidating..." : "Save & Revalidate"}
        </button>
      )}
    </div>
  );
}
