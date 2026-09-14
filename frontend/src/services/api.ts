import axios from "axios";

export type TrafficLight = "GREEN" | "YELLOW" | "RED";

export interface ExtractedFields {
  invoice_recipient?: string | null;
  vendor_name?: string | null;
  invoice_number?: string | null;
  invoice_date?: string | null;
  service_date?: string | null;
  currency?: string | null;
  net_amount?: number | null;
  vat_rate?: number | null;
  vat_amount?: number | null;
  gross_amount?: number | null;
  description?: string | null;
}

export interface ValidationResult {
  check: string;
  severity: "RED" | "YELLOW" | "GREEN" | "LOGIC";
  status: "PASS" | "FAIL" | "WARN";
  details: string;
}

export interface BookingLine {
  side: "DEBIT" | "CREDIT";
  account: string;
  name?: string | null;
  amount: number;
}

export interface SuggestedAccount {
  account: string;
  name: string;
}

export interface AuditInfo {
  processed_at: string;
  model_or_method: string;
  notes: string;
}

export interface InvoiceRecord {
  id: string;
  invoice_file: string;
  original_filename?: string;
  extracted: ExtractedFields;
  validations: ValidationResult[];
  suggested_expense_account: SuggestedAccount | null;
  traffic_light: TrafficLight;
  decision_reasons: string[];
  booking_proposal: BookingLine[];
  blocked: boolean;
  audit: AuditInfo;
}

export interface MasterData {
  clients: Record<string, any>[];
  creditors: Record<string, any>[];
  accounts: Record<string, any>[];
}

const client = axios.create({ baseURL: "/api" });

export async function uploadInvoice(file: File): Promise<InvoiceRecord> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await client.post<InvoiceRecord>("/invoices/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listInvoices(): Promise<InvoiceRecord[]> {
  const { data } = await client.get<InvoiceRecord[]>("/invoices");
  return data;
}

export async function getInvoice(id: string): Promise<InvoiceRecord> {
  const { data } = await client.get<InvoiceRecord>(`/invoices/${id}`);
  return data;
}

export function getInvoicePdfUrl(id: string): string {
  return `/api/invoices/${id}/pdf`;
}

export async function revalidateInvoice(
  id: string,
  extracted: Partial<ExtractedFields>
): Promise<InvoiceRecord> {
  const { data } = await client.post<InvoiceRecord>(`/invoices/${id}/revalidate`, {
    extracted,
  });
  return data;
}

export async function getMasterData(): Promise<MasterData> {
  const { data } = await client.get<MasterData>("/master-data");
  return data;
}
