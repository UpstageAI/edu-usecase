import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  ArrowLeft,
  CalendarDays,
  FileText,
  Loader2,
  Sparkles,
  Star,
  ThumbsUp,
  Timer,
  Coins,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import MermaidContent from "@/components/report/MermaidContent";
import {
  DocumentInsightsPayload,
  OcrProvider,
  ProviderEvaluation,
  PageProviderResult,
  fetchDocumentInsights,
  updateDocumentSelection,
} from "@/lib/api-client";
import { useIsClamped } from "@/hooks/useClampled";
import { cn } from "@/lib/utils";
import formatDateTime from "@/utils/formatDateTime";

const providerDisplay = (provider?: OcrProvider | null, evaluations: ProviderEvaluation[] = []) => {
  if (!provider) return "-";
  const match = evaluations.find((item) => item.provider === provider);
  return match?.displayName ?? provider;
};

const formatDuration = (value?: number | null) => {
  if (value === null || value === undefined) {
    return "-";
  }
  if (value >= 60_000) {
    return `${(value / 60_000).toFixed(1)}분`;
  }
  if (value >= 1_000) {
    const decimals = value >= 10_000 ? 0 : 1;
    return `${(value / 1_000).toFixed(decimals)}초`;
  }
  return `${Math.round(value)}ms`;
};

const formatCost = (value?: number | null) => {
  if (value === null || value === undefined) {
    return "-";
  }
  if (value >= 1) {
    return `${value.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}원`;
  }
  if (value >= 0.01) {
    return `${value.toLocaleString("ko-KR", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}원`;
  }
  return `${value.toFixed(4)}원`;
};

type PageProviderTableRow = {
  provider: OcrProvider;
  displayName: string;
  text: string;
  validity?: string | boolean | null;
  quality: number | null;
  timePerPageMs: number | null;
  costPerPage: number | null;
  isBestQuality: boolean;
  isFastest: boolean;
  isMostAffordable: boolean;
  isSelected: boolean;
  isRecommended: boolean;
};

const formatValidity = (value?: string | boolean | null) => {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (typeof value === "boolean") {
    return value ? "정상" : "검증 필요";
  }
  return value;
};

interface ClampedTextCellProps {
  text: string;
}

const ClampedTextCell = ({ text }: ClampedTextCellProps) => {
  const [expanded, setExpanded] = useState(false);
  const { ref, clamped } = useIsClamped<HTMLDivElement>([text, expanded]);

  if (!text?.trim()) {
    return <span className="text-xs text-muted-foreground">결과 없음</span>;
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <div
        ref={ref}
        className={cn(
          "whitespace-pre-wrap text-sm text-foreground",
          expanded ? "" : "line-clamp-3",
        )}
      >
        {text}
      </div>
      {(clamped || expanded) && (
        <Button
          variant="ghost"
          size="sm"
          className="h-6 shrink-0 px-2"
          onClick={() => setExpanded((prev) => !prev)}
          aria-expanded={expanded}
        >
          {expanded ? "간략히" : "더보기"}
        </Button>
      )}
    </div>
  );
};

const DocumentInsights = () => {
  const navigate = useNavigate();
  const { documentId } = useParams<{ documentId: string }>();
  const queryClient = useQueryClient();
  const [selectedPageIndex, setSelectedPageIndex] = useState(0);

  const { data, isLoading, isError, error } = useQuery<DocumentInsightsPayload>({
    queryKey: ["document-insights", documentId],
    queryFn: () => fetchDocumentInsights(documentId ?? ""),
    enabled: Boolean(documentId),
  });

  const selectionMutation = useMutation({
    mutationFn: (provider: OcrProvider) => updateDocumentSelection(documentId ?? "", provider),
    onSuccess: (summary) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.setQueryData(
        ["document-insights", documentId],
        (prev: DocumentInsightsPayload | undefined) => {
          if (!prev) return prev;
          return {
            ...prev,
            document: {
              ...prev.document,
              ...summary,
              recommendedStrategy: summary.recommendedStrategy ?? prev.document.recommendedStrategy,
              recommendationNotes: summary.recommendationNotes ?? prev.document.recommendationNotes,
            },
          };
        },
      );
      queryClient.invalidateQueries({ queryKey: ["document-insights", documentId] });
      toast.success("선택한 API를 업데이트했습니다");
    },
    onError: (mutationError: unknown) => {
      toast.error((mutationError as Error)?.message ?? "API 선택을 변경하지 못했습니다");
    },
  });

  const pages = data?.pages ?? [];
  const providerEvaluationsList = useMemo(
    () => data?.providerEvaluations ?? [],
    [data?.providerEvaluations],
  );
  const selectedStrategy = data?.document.selectedStrategy;
  const recommendedStrategy = data?.document.recommendedStrategy;

  useEffect(() => {
    setSelectedPageIndex(0);
  }, [documentId, pages.length]);

  const currentPage = pages[selectedPageIndex];
  const providerResultsMap = useMemo(() => {
    const map = new Map<OcrProvider, PageProviderResult>();
    currentPage?.providerResults?.forEach((item) => {
      map.set(item.provider, item);
    });
    return map;
  }, [currentPage?.providerResults]);

  const providerRows = useMemo<PageProviderTableRow[]>(() => {
    if (!providerEvaluationsList.length) {
      return [];
    }

    return providerEvaluationsList.map((evaluation) => {
      const providerResult = providerResultsMap.get(evaluation.provider);
      const mergedText = providerResult?.textContent ?? currentPage?.textContent ?? "";

      return {
        provider: evaluation.provider,
        displayName: providerResult?.displayName ?? evaluation.displayName,
        text: mergedText,
        validity: providerResult?.validity ?? null,
        quality: providerResult?.llmJudgeScore ?? evaluation.llmJudgeScore ?? null,
        timePerPageMs: providerResult?.processingTimeMs ?? evaluation.timePerPageMs ?? null,
        costPerPage: providerResult?.costPerPage ?? evaluation.costPerPage ?? null,
        isBestQuality: evaluation.isBestQuality,
        isFastest: evaluation.isFastest,
        isMostAffordable: evaluation.isMostAffordable,
        isSelected: selectedStrategy === evaluation.provider,
        isRecommended: recommendedStrategy === evaluation.provider,
      };
    });
  }, [
    providerEvaluationsList,
    providerResultsMap,
    currentPage?.textContent,
    selectedStrategy,
    recommendedStrategy,
  ]);

  const documentPagesCount = data?.document?.pagesCount ?? pages.length;

  const recommendedEvaluation = useMemo(() => {
    if (!recommendedStrategy) {
      return null;
    }
    return providerEvaluationsList.find((item) => item.provider === recommendedStrategy) ?? null;
  }, [providerEvaluationsList, recommendedStrategy]);

  const selectedEvaluation = useMemo(() => {
    if (!selectedStrategy) {
      return null;
    }
    return providerEvaluationsList.find((item) => item.provider === selectedStrategy) ?? null;
  }, [providerEvaluationsList, selectedStrategy]);

  const totalTimeSummary = useMemo(() => {
    if (recommendedEvaluation) {
      return {
        kind: "recommended" as const,
        value: recommendedEvaluation.estimatedTotalTimeMs,
      };
    }
    if (!providerEvaluationsList.length) {
      return null;
    }
    const times = providerEvaluationsList.map((item) => item.estimatedTotalTimeMs);
    const min = Math.min(...times);
    const max = Math.max(...times);
    return {
      kind: "range" as const,
      min,
      max,
    };
  }, [providerEvaluationsList, recommendedEvaluation]);

  const totalCostSummary = useMemo(() => {
    if (recommendedEvaluation && recommendedEvaluation.estimatedTotalCost != null) {
      return {
        kind: "recommended" as const,
        value: recommendedEvaluation.estimatedTotalCost,
      };
    }
    const costs = providerEvaluationsList
      .map((item) => item.estimatedTotalCost)
      .filter((value): value is number => value != null);
    if (!costs.length) {
      return null;
    }
    const min = Math.min(...costs);
    const max = Math.max(...costs);
    return {
      kind: "range" as const,
      min,
      max,
    };
  }, [providerEvaluationsList, recommendedEvaluation]);

  const metricEvaluation = recommendedEvaluation ?? selectedEvaluation ?? null;
  const metricContextLabel = recommendedEvaluation
    ? "추천된 API 기준"
    : selectedEvaluation
      ? "선택한 API 기준"
      : null;

  const handlePageChange = (direction: "prev" | "next") => {
    if (!pages.length) return;
    setSelectedPageIndex((prev) => {
      if (direction === "prev") {
        return prev === 0 ? prev : prev - 1;
      }
      return prev >= pages.length - 1 ? prev : prev + 1;
    });
  };

  const handleProviderSelection = (provider: OcrProvider) => {
    if (!documentId) return;
    if (provider === data?.document.selectedStrategy) {
      toast.info("이미 선택된 API입니다");
      return;
    }
    selectionMutation.mutate(provider);
  };

  if (!documentId) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-background via-accent/30 to-background">
        <div className="text-sm text-muted-foreground">분석할 문서를 선택해주세요.</div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-background via-accent/30 to-background">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          분석 데이터를 불러오는 중입니다...
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-background via-accent/30 to-background">
        <Card className="max-w-md text-center">
          <CardHeader>
            <CardTitle>문서 분석 데이터를 찾을 수 없습니다</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              {(error as Error)?.message ?? "문서를 다시 선택한 뒤 시도해주세요."}
            </p>
            <Button onClick={() => navigate("/analysis")}>분석 현황으로 이동</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { document, agentStatuses, mermaidChart } = data;
  const totalPages = pages.length;

  return (
    <div className="flex h-full w-full overflow-y-auto bg-gradient-to-br from-background via-accent/30 to-background">
      <div className="container mx-auto flex-1 px-5 py-5 flex flex-col gap-6 h-fit">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate("/analysis")}
              className="hover:bg-muted"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-secondary">
                <FileText className="h-6 w-6 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-xl font-bold">문서 분석 요약</h1>
                <p className="text-xs text-muted-foreground">문서 ID: {document.id}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">파일명</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-base font-semibold text-foreground break-words">
                {document.originalName}
              </p>
              <p className="mt-2 text-xs text-muted-foreground">저장 이름: {document.storedName}</p>
              {document.benchmarkUrl && (
                <Button variant="link" size="sm" asChild className="px-0 text-primary">
                  <a href={document.benchmarkUrl} target="_blank" rel="noreferrer">
                    벤치마크 보기
                  </a>
                </Button>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">총 페이지</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold text-foreground">{document.pagesCount}</p>
              <p className="mt-2 text-xs text-muted-foreground">추출된 페이지 수 기준</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">처리 일시</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-foreground">
                <CalendarDays className="h-4 w-4 text-muted-foreground" />
                <span>{formatDateTime(document.processedAt)}</span>
              </div>
              <p className="text-xs text-muted-foreground">
                상태: {document.status === "processed" ? "처리 완료" : document.status}
              </p>
            </CardContent>
          </Card>
        </div>

        <section className="flex flex-col gap-4">
          <Card className="flex flex-col">
            <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary" />
                  <CardTitle className="text-lg font-semibold text-foreground">
                    페이지별 OCR 비교
                  </CardTitle>
                </div>
                {document.recommendedStrategy && (
                  <Badge variant="secondary" className="gap-1">
                    <Star className="h-3 w-3" />
                    추천: {providerDisplay(document.recommendedStrategy, providerEvaluationsList)}
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Button
                  size="icon"
                  variant="outline"
                  onClick={() => handlePageChange("prev")}
                  disabled={selectedPageIndex === 0}
                >
                  <ArrowLeft className="h-4 w-4" />
                </Button>
                <Badge variant="outline">
                  {totalPages ? `${selectedPageIndex + 1} / ${totalPages}` : "-"}
                </Badge>
                <Button
                  size="icon"
                  variant="outline"
                  onClick={() => handlePageChange("next")}
                  disabled={selectedPageIndex >= totalPages - 1}
                >
                  <ArrowLeft className="h-4 w-4 rotate-180" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="grid gap-6 lg:grid-cols-[1.15fr_1.85fr]">
              <div className="flex h-full min-h-[320px] items-center justify-center rounded-xl border border-dashed border-border bg-muted/30 p-2">
                {currentPage?.imagePath ? (
                  <img
                    src={currentPage.imagePath}
                    alt={`문서 페이지 ${currentPage.pageNumber}`}
                    className="max-h-[460px] w-full rounded-lg object-contain shadow-sm"
                  />
                ) : (
                  <div className="text-center text-sm text-muted-foreground">
                    {pages.length > 0
                      ? "페이지 이미지가 아직 준비되지 않았습니다."
                      : "표시할 페이지 데이터가 없습니다."}
                  </div>
                )}
              </div>
              <ScrollArea className="max-h-[520px] w-full rounded-xl border border-border bg-card">
                <div className="min-w-[720px]">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[200px] whitespace-nowrap">
                          API 라이브러리
                        </TableHead>
                        <TableHead className="w-[300px] whitespace-nowrap">
                          텍스트 추출 결과
                        </TableHead>
                        <TableHead className="w-[100px] whitespace-nowrap text-center">
                          유효성
                        </TableHead>
                        <TableHead className="w-[120px] whitespace-nowrap text-center">
                          품질 (LLM-Judge)
                        </TableHead>
                        <TableHead className="w-[140px] whitespace-nowrap text-center">
                          페이지별 처리 시간
                        </TableHead>
                        <TableHead className="w-[140px] whitespace-nowrap text-center">
                          페이지별 비용
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {providerRows.length === 0 ? (
                        <TableRow>
                          <TableCell
                            colSpan={6}
                            className="text-center text-sm text-muted-foreground"
                          >
                            평가 데이터가 아직 준비되지 않았습니다.
                          </TableCell>
                        </TableRow>
                      ) : (
                        providerRows.map((row) => {
                          const rowAccent =
                            row.isBestQuality && row.isFastest && row.isMostAffordable
                              ? "border-l-4 border-primary bg-primary/10"
                              : row.isBestQuality && row.isFastest
                                ? "border-l-4 border-lime-400 bg-lime-50/60"
                                : row.isBestQuality
                                  ? "border-l-4 border-amber-400 bg-amber-50/60"
                                  : row.isFastest
                                    ? "border-l-4 border-emerald-400 bg-emerald-50/40"
                                    : row.isMostAffordable
                                      ? "border-l-4 border-sky-400 bg-sky-50/60"
                                      : "border-l-4 border-transparent";

                          return (
                            <TableRow key={row.provider} className={cn("align-top", rowAccent)}>
                              <TableCell className="w-[200px] align-top text-sm text-foreground">
                                <div className="flex flex-col gap-2">
                                  <div className="flex flex-wrap items-center gap-2">
                                    <span className="font-semibold">{row.displayName}</span>
                                    {row.isRecommended && (
                                      <Badge variant="secondary" className="gap-1 px-2 py-0">
                                        <Star className="h-3 w-3" />
                                        추천
                                      </Badge>
                                    )}
                                    {row.isSelected && (
                                      <Badge variant="outline" className="gap-1 px-2 py-0">
                                        <ThumbsUp className="h-3 w-3" />
                                        선택됨
                                      </Badge>
                                    )}
                                  </div>
                                  <div className="flex flex-wrap gap-2">
                                    {row.isBestQuality && (
                                      <Badge
                                        className="bg-amber-500 text-amber-950"
                                        variant="secondary"
                                      >
                                        최고 품질
                                      </Badge>
                                    )}
                                    {row.isFastest && (
                                      <Badge
                                        className="bg-emerald-500 text-emerald-950"
                                        variant="secondary"
                                      >
                                        최단 시간
                                      </Badge>
                                    )}
                                    {row.isMostAffordable && (
                                      <Badge
                                        className="bg-sky-500 text-sky-950"
                                        variant="secondary"
                                      >
                                        최저 비용
                                      </Badge>
                                    )}
                                  </div>
                                </div>
                              </TableCell>
                              <TableCell className="w-[300px] align-top">
                                <ClampedTextCell text={row.text} />
                              </TableCell>
                              <TableCell className="w-[100px] align-top text-sm text-foreground text-center">
                                {formatValidity(row.validity)}
                              </TableCell>
                              <TableCell className="w-[120px] align-top text-center text-sm text-foreground">
                                {row.quality != null ? row.quality.toFixed(1) : "-"}
                              </TableCell>
                              <TableCell className="w-[140px] align-top text-center text-sm text-foreground">
                                {formatDuration(row.timePerPageMs)}
                              </TableCell>
                              <TableCell className="w-[140px] align-top text-center text-sm text-foreground">
                                {formatCost(row.costPerPage)}
                              </TableCell>
                            </TableRow>
                          );
                        })
                      )}
                    </TableBody>
                  </Table>
                </div>

                <ScrollBar orientation="horizontal" />
                <ScrollBar orientation="vertical" />
              </ScrollArea>
            </CardContent>
          </Card>
        </section>

        <section>
          <Card className="grid gap-30 p-6 lg:grid-cols-[1.6fr_1fr]">
            <div className="space-y-4">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                  <Badge variant="secondary" className="gap-1 px-2 py-0">
                    <Star className="h-3 w-3" />
                    추천 API
                  </Badge>
                  <span className="text-lg font-semibold text-foreground">
                    {document.recommendedStrategy
                      ? providerDisplay(document.recommendedStrategy, providerEvaluationsList)
                      : "추천 정보를 계산 중입니다"}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {document.recommendationNotes ??
                    "품질과 처리 시간 데이터를 바탕으로 추천 결과를 계산 중입니다."}
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <div className="flex flex-col gap-1 rounded-lg border border-border p-3">
                  <span className="text-xs font-semibold text-muted-foreground tracking-wide">
                    총 처리 시간
                  </span>
                  <div className="flex items-center gap-2 text-sm text-foreground">
                    <Timer className="h-4 w-4 text-primary" />
                    {totalTimeSummary ? (
                      totalTimeSummary.kind === "recommended" ? (
                        <span>
                          {formatDuration(totalTimeSummary.value)} (총 {documentPagesCount} 페이지)
                        </span>
                      ) : (
                        <span>
                          {`${formatDuration(totalTimeSummary.min)} ~ ${formatDuration(totalTimeSummary.max)}`}
                          (총
                          {documentPagesCount} 페이지)
                        </span>
                      )
                    ) : (
                      <span>계산 가능한 시간 정보가 없습니다.</span>
                    )}
                  </div>
                </div>

                <div className="flex flex-col gap-1 rounded-lg border border-border p-3">
                  <span className="text-xs font-semibold text-muted-foreground tracking-wide">
                    총 비용
                  </span>
                  <div className="flex items-center gap-2 text-sm text-foreground">
                    <Coins className="h-4 w-4 text-primary" />
                    {totalCostSummary ? (
                      totalCostSummary.kind === "recommended" ? (
                        <span>
                          {formatCost(totalCostSummary.value)} (총 {documentPagesCount} 페이지)
                        </span>
                      ) : (
                        <span>
                          {`${formatCost(totalCostSummary.min)} ~ ${formatCost(totalCostSummary.max)}`}{" "}
                          (총
                          {documentPagesCount} 페이지)
                        </span>
                      )
                    ) : (
                      <span>계산 가능한 비용 정보가 없습니다.</span>
                    )}
                  </div>
                </div>

                <div className="flex flex-col gap-1 rounded-lg border border-border p-3">
                  <span className="text-xs font-semibold text-muted-foreground tracking-wide">
                    추천 지표
                  </span>
                  {metricContextLabel && (
                    <span className="text-xs text-muted-foreground">{metricContextLabel}</span>
                  )}
                  {metricEvaluation ? (
                    <div className="flex flex-col gap-1 text-sm text-foreground">
                      <span className="flex items-center gap-1">
                        <Sparkles className="h-4 w-4 text-primary" />
                        {metricEvaluation.llmJudgeScore.toFixed(1)} 점
                      </span>
                      <span className="flex items-center gap-1 text-muted-foreground">
                        <Timer className="h-3 w-3" />
                        {formatDuration(metricEvaluation.timePerPageMs)} / 페이지
                      </span>
                      {metricEvaluation.costPerPage != null && (
                        <span className="flex items-center gap-1 text-muted-foreground">
                          <Coins className="h-3 w-3" />
                          {formatCost(metricEvaluation.costPerPage)} / 페이지
                        </span>
                      )}
                      {metricEvaluation.estimatedTotalCost != null && (
                        <span className="flex items-center gap-1 text-muted-foreground">
                          <Coins className="h-3 w-3" />
                          {formatCost(metricEvaluation.estimatedTotalCost)} (총 {documentPagesCount}{" "}
                          페이지)
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="text-sm text-muted-foreground">
                      추천 지표를 준비 중입니다.
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-3 justify-evenly">
              <div className="flex flex-col gap-2">
                <h4 className="text-sm font-semibold text-muted-foreground">API 선택 변경</h4>
                <p className="text-xs text-muted-foreground">
                  원하는 공급자를 선택하면 해당 결과가 보고서에 반영됩니다.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {providerEvaluationsList.length === 0 ? (
                  <p className="text-xs text-muted-foreground">선택 가능한 API가 없습니다.</p>
                ) : (
                  providerEvaluationsList.map((item) => {
                    const isActive = document.selectedStrategy === item.provider;
                    const isRecommendedChoice = document.recommendedStrategy === item.provider;

                    return (
                      <Button
                        key={item.provider}
                        variant={isActive ? "default" : "outline"}
                        className={cn(
                          "gap-2",
                          isActive &&
                            "bg-gradient-to-r from-primary to-secondary text-primary-foreground shadow-sm",
                          !isActive && isRecommendedChoice && "border-primary/40 text-primary",
                        )}
                        onClick={() => handleProviderSelection(item.provider)}
                        disabled={selectionMutation.isPending}
                      >
                        {selectionMutation.isPending &&
                        document.selectedStrategy !== item.provider ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : isActive ? (
                          <ThumbsUp className="h-4 w-4" />
                        ) : isRecommendedChoice ? (
                          <Star className="h-4 w-4 text-primary" />
                        ) : (
                          <Sparkles className="h-4 w-4 text-primary" />
                        )}
                        {item.displayName}
                      </Button>
                    );
                  })
                )}
              </div>
            </div>
          </Card>
        </section>

        <section className="grid gap-4 lg:grid-cols-[1fr_1.8fr]">
          <Card className="flex flex-col">
            <CardHeader>
              <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
                Multi-Agent 상태
              </CardTitle>
            </CardHeader>
            <div className="flex flex-col gap-3 px-4">
              {agentStatuses.length === 0 ? (
                <p className="text-sm text-muted-foreground">등록된 에이전트 상태가 없습니다.</p>
              ) : (
                agentStatuses.map((status) => (
                  <div
                    key={status.agentName}
                    className="flex items-center justify-between rounded-lg border border-border px-3 py-2 gap-1"
                  >
                    <div className="flex flex-col gap-1">
                      <span className="text-sm font-semibold text-foreground">
                        {status.agentName}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {status.description ?? "-"}
                      </span>
                    </div>
                    <Badge variant="outline" className="capitalize">
                      {status.status}
                    </Badge>
                  </div>
                ))
              )}
            </div>
          </Card>
          <MermaidContent chart={mermaidChart} />
        </section>
      </div>
    </div>
  );
};

export default DocumentInsights;
