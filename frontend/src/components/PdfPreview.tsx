import { useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from "lucide-react";
import { getInvoicePdfUrl, type InvoiceRecord } from "../services/api";

pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

export default function PdfPreview({ invoiceId, invoice }: { invoiceId: string | null; invoice?: InvoiceRecord | null }) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.1);

  if (!invoiceId) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400 text-sm">
        Select or upload an invoice to preview it here.
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 bg-white text-sm">
        <div className="flex items-center gap-2">
          <button
            className="p-1 rounded hover:bg-gray-100 disabled:opacity-30"
            disabled={pageNumber <= 1}
            onClick={() => setPageNumber((p) => Math.max(1, p - 1))}
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span>
            Page {pageNumber} / {numPages || "?"}
          </span>
          <button
            className="p-1 rounded hover:bg-gray-100 disabled:opacity-30"
            disabled={pageNumber >= numPages}
            onClick={() => setPageNumber((p) => Math.min(numPages, p + 1))}
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
        <div className="flex items-center gap-2">
          <button className="p-1 rounded hover:bg-gray-100" onClick={() => setScale((s) => Math.max(0.5, s - 0.1))}>
            <ZoomOut className="w-4 h-4" />
          </button>
          <button className="p-1 rounded hover:bg-gray-100" onClick={() => setScale((s) => Math.min(2.5, s + 0.1))}>
            <ZoomIn className="w-4 h-4" />
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-auto bg-gray-100 flex justify-center p-4">
        <Document
          key={invoiceId}
          file={`${getInvoicePdfUrl(invoiceId)}?v=${encodeURIComponent(invoice?.audit?.processed_at || "")}`}
          onLoadSuccess={({ numPages }) => {
            setNumPages(numPages);
            setPageNumber(1);
          }}
          loading={<p className="text-sm text-gray-400">Loading PDF...</p>}
          error={<p className="text-sm text-rose-500">Failed to load PDF.</p>}
        >
          <Page pageNumber={pageNumber} scale={scale} />
        </Document>
      </div>
    </div>
  );
}
