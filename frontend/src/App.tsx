import { useCallback, useEffect, useState } from "react";
import InvoiceSelector from "./components/InvoiceSelector";
import PdfPreview from "./components/PdfPreview";
import TrafficLightBadge from "./components/TrafficLightBadge";
import ExtractedDataForm from "./components/ExtractedDataForm";
import ValidationResults from "./components/ValidationResults";
import BookingProposalTable from "./components/BookingProposalTable";
import {
  InvoiceRecord,
  ExtractedFields,
  listInvoices,
  uploadInvoice,
  getInvoice,
  revalidateInvoice,
} from "./services/api";

export default function App() {
  const [invoices, setInvoices] = useState<InvoiceRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedInvoice, setSelectedInvoice] = useState<InvoiceRecord | null>(null);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Only show invoices uploaded via this UI session
  const [uploadedIds, setUploadedIds] = useState<string[]>([]);

  const refreshList = useCallback(async () => {
    try {
      const data = await listInvoices();
      setInvoices(data);
    } catch (e) {
      setError("Failed to load invoice list. Is the backend running on :8000?");
    }
  }, []);

  useEffect(() => {
    refreshList();
  }, [refreshList]);

  useEffect(() => {
    if (!selectedId) {
      setSelectedInvoice(null);
      return;
    }
    getInvoice(selectedId).then(setSelectedInvoice).catch(() => setError("Failed to load invoice detail."));
  }, [selectedId]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const created = await uploadInvoice(file);
      await refreshList();
      setSelectedId(created.id);
      setUploadedIds((prev) => Array.from(new Set([...prev, created.id])));
    } catch (e) {
      setError("Upload failed. Ensure the file is a valid PDF and the backend is reachable.");
    } finally {
      setUploading(false);
    }
  };

  const handleRevalidate = async (updated: Partial<ExtractedFields>) => {
    if (!selectedId) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await revalidateInvoice(selectedId, updated);
      setSelectedInvoice(result);
      await refreshList();
    } catch (e) {
      setError("Revalidation failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-gray-50">
      <header className="border-b border-gray-200 bg-white px-4 py-3">
        <h1 className="text-lg font-bold text-slate-900">Automated Invoice-to-Booking System</h1>
      </header>

      {error && (
        <div className="bg-rose-50 text-rose-700 text-sm px-4 py-2 border-b border-rose-200">{error}</div>
      )}

      <div className="flex flex-1 overflow-hidden">
        <div className="w-64 border-r border-gray-200 bg-white flex-shrink-0">
          <InvoiceSelector
            invoices={invoices.filter((inv) => uploadedIds.includes(inv.id))}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onUpload={handleUpload}
            uploading={uploading}
          />
        </div>

        <div className="flex-1 border-r border-gray-200">
          <PdfPreview invoiceId={selectedId} invoice={selectedInvoice} />
        </div>

        <div className="w-[480px] flex-shrink-0 overflow-y-auto p-4 space-y-4">
          {!selectedInvoice ? (
            <p className="text-sm text-gray-400">Select an invoice to view its evaluation.</p>
          ) : (
            <>
              <TrafficLightBadge status={selectedInvoice.traffic_light} />
              <ExtractedDataForm
                extracted={selectedInvoice.extracted}
                editable={selectedInvoice.traffic_light === "YELLOW"}
                submitting={submitting}
                onSubmit={handleRevalidate}
              />
              <ValidationResults validations={selectedInvoice.validations} />
              <BookingProposalTable invoice={selectedInvoice} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
