import type { ApiErrorBody, AuditJob, AuditRequest, DatasetSummary, DemoDescriptor, Health } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  code: string;
  field?: string;
  constructor(code: string, message: string, field?: string) {
    super(message);
    this.code = code;
    this.field = field;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError("network", "Could not reach the compute server. It may still be waking up; try again in a moment.");
  }
  if (!response.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      /* non-JSON error body */
    }
    if (body?.error?.code) throw new ApiError(body.error.code, body.error.message, body.error.field);
    throw new ApiError("http_error", `The server answered with HTTP ${response.status}.`);
  }
  return (await response.json()) as T;
}

export const getHealth = () => request<Health>("/api/health");
export const getDemos = () => request<DemoDescriptor[]>("/api/demos");
export const loadDemo = (id: string) =>
  request<DatasetSummary>(`/api/datasets/demo/${encodeURIComponent(id)}`, { method: "POST" });

export function uploadDataset(file: File) {
  const form = new FormData();
  form.append("file", file);
  return request<DatasetSummary>("/api/datasets", { method: "POST", body: form });
}

export const createAudit = (body: AuditRequest) =>
  request<AuditJob>("/api/audits", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const getAudit = (id: string) => request<AuditJob>(`/api/audits/${encodeURIComponent(id)}`);

export const reportJsonUrl = (id: string) => `${API_URL}/api/audits/${encodeURIComponent(id)}/report.json`;
