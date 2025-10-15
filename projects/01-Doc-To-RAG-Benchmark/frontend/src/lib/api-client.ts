import { QueryClient } from "@tanstack/react-query";

export type DocumentStatus = "uploaded" | "processing" | "processed" | "failed";
export type OcrProvider = string;

export interface DocumentSummary {
  id: string;
  originalName: string;
  storedName: string;
  sizeBytes: number;
  extension?: string | null;
  language?: string | null;
  status: DocumentStatus;
  uploadedAt: string;
  processedAt?: string | null;
  qualityScore?: number | null;
  pagesCount: number;
  analysisItemsCount: number;
  recommendedStrategy?: OcrProvider | null;
  recommendationNotes?: string | null;
  selectedStrategy?: OcrProvider | null;
  selectionRationale?: string | null;
  ocrSpeedMsPerPage?: number | null;
  benchmarkUrl?: string | null;
}

export interface AnalysisItem {
  id: number;
  documentId: string;
  question: string;
  answer: string;
  contextType: string;
  confidence: number;
  pageNumber: number;
  documentName: string;
}

export interface ProviderEvaluation {
  provider: OcrProvider;
  displayName: string;
  llmJudgeScore: number;
  timePerPageMs: number;
  estimatedTotalTimeMs: number;
  costPerPage: number | null;
  estimatedTotalCost: number | null;
  qualityNotes?: string | null;
  latencyMs?: number | null;
  isBestQuality: boolean;
  isFastest: boolean;
  isMostAffordable: boolean;
}

export interface PageProviderResult {
  provider: OcrProvider;
  textContent: string;
  validity?: string | boolean | null;
  llmJudgeScore?: number | null;
  processingTimeMs?: number | null;
  costPerPage?: number | null;
  remarks?: string | null;
  displayName?: string | null;
}

export interface PagePreview {
  pageNumber: number;
  imagePath?: string | null;
  textContent: string;
  providerResults?: PageProviderResult[];
}

export interface ReportAgentStatus {
  agentName: string;
  status: "pending" | "running" | "completed" | "failed";
  description?: string | null;
}

export interface DocumentInsightsPayload {
  document: DocumentSummary;
  providerEvaluations: ProviderEvaluation[];
  pages: PagePreview[];
  agentStatuses: ReportAgentStatus[];
  mermaidChart?: string | null;
  selectionRationale?: string | null;
}

interface ApiErrorBody {
  detail?: string;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `요청 실패 (status ${response.status})`;
    try {
      const payload = (await response.json()) as ApiErrorBody;
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // ignore - response body may be empty
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

function mapDocumentSummary(raw: any): DocumentSummary {
  return {
    id: raw.id,
    originalName: raw.original_name,
    storedName: raw.stored_name,
    sizeBytes: raw.size_bytes,
    extension: raw.extension ?? null,
    language: raw.language ?? null,
    status: raw.status,
    uploadedAt: raw.uploaded_at,
    processedAt: raw.processed_at ?? null,
    qualityScore: raw.quality_score ?? null,
    pagesCount: raw.pages_count,
    analysisItemsCount: raw.analysis_items_count,
    recommendedStrategy: raw.recommended_strategy ?? null,
    recommendationNotes: raw.recommendation_notes ?? null,
    selectedStrategy: raw.selected_strategy ?? null,
    selectionRationale: raw.selection_rationale ?? null,
    ocrSpeedMsPerPage: raw.ocr_speed_ms_per_page ?? null,
    benchmarkUrl: raw.benchmark_url ?? null,
  };
}

function mapAnalysisItem(raw: any): AnalysisItem {
  return {
    id: raw.id,
    documentId: raw.document_id,
    question: raw.question,
    answer: raw.answer,
    contextType: raw.context_type,
    confidence: raw.confidence,
    pageNumber: raw.page_number,
    documentName: raw.document_name,
  };
}

function mapReportAgentStatus(raw: any): ReportAgentStatus {
  return {
    agentName: raw.agent_name,
    status: raw.status,
    description: raw.description ?? null,
  };
}

function mapProviderEvaluation(raw: any): ProviderEvaluation {
  return {
    provider: raw.provider,
    displayName: raw.display_name,
    llmJudgeScore: raw.llm_judge_score,
    timePerPageMs: raw.time_per_page_ms,
    estimatedTotalTimeMs: raw.estimated_total_time_ms,
    costPerPage: raw.cost_per_page ?? null,
    estimatedTotalCost: raw.estimated_total_cost ?? null,
    qualityNotes: raw.quality_notes ?? null,
    latencyMs: raw.latency_ms ?? null,
    isBestQuality: raw.is_best_quality,
    isFastest: raw.is_fastest,
    isMostAffordable: raw.is_most_affordable,
  };
}

function mapPagePreview(raw: any): PagePreview {
  const providerResults = Array.isArray(raw.provider_results)
    ? raw.provider_results.map((item: any) => ({
        provider: (item.provider ?? "") as OcrProvider,
        textContent: item.text_content ?? "",
        validity: item.validity ?? null,
        llmJudgeScore: item.llm_judge_score ?? null,
        processingTimeMs: item.processing_time_ms ?? null,
        costPerPage: item.cost_per_page ?? null,
        remarks: item.remarks ?? item.notes ?? null,
        displayName: item.display_name ?? null,
      }))
    : undefined;

  return {
    pageNumber: raw.page_number,
    imagePath: raw.image_path ?? null,
    textContent: raw.text_content,
    providerResults,
  };
}

export async function fetchDocuments(): Promise<DocumentSummary[]> {
  const response = await fetch("/api/documents");
  const data = await handleResponse<{ items: any[] }>(response);
  return data.items.map(mapDocumentSummary);
}

export async function fetchAnalysisItems(): Promise<AnalysisItem[]> {
  const response = await fetch("/api/analysis-items");
  const data = await handleResponse<{ items: any[] }>(response);
  return data.items.map(mapAnalysisItem);
}

export async function fetchDocumentInsights(documentId: string): Promise<DocumentInsightsPayload> {
  const response = await fetch(`/api/documents/${documentId}/insights`);
  const data = await handleResponse<any>(response);
  return {
    document: mapDocumentSummary(data.document),
    providerEvaluations: (data.provider_evaluations ?? []).map(mapProviderEvaluation),
    pages: (data.pages ?? []).map(mapPagePreview),
    agentStatuses: (data.agent_statuses ?? []).map(mapReportAgentStatus),
    mermaidChart: data.mermaid_chart ?? null,
    selectionRationale: data.selection_rationale ?? null,
  };
}

export async function updateDocumentSelection(
  documentId: string,
  provider: OcrProvider,
): Promise<DocumentSummary> {
  const response = await fetch(`/api/documents/${documentId}/selection`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider }),
  });
  const data = await handleResponse<any>(response);
  return mapDocumentSummary(data);
}

export interface UploadDocumentPayload {
  file: File;
  apiKey: string;
}

export async function uploadDocument({
  file,
  apiKey,
}: UploadDocumentPayload): Promise<DocumentSummary> {
  if (!apiKey) {
    throw new Error("API 키가 필요합니다.");
  }

  const formData = new FormData();
  formData.append("file", file);

  const requestInit: RequestInit = {
    method: "POST",
    body: formData,
  };

  if (apiKey) {
    requestInit.headers = {
      "x-ocr-api-key": apiKey,
    };
  }

  const response = await fetch("/api/uploads", requestInit);

  const data = await handleResponse<{ document: any }>(response);
  return mapDocumentSummary(data.document);
}

export const queryClient = new QueryClient();
