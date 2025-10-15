import { useMemo, useState } from "react";
import { FileText, FileBarChart, Search, Sparkles, Timer, Link as LinkIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { DocumentSummary, fetchDocuments } from "@/lib/api-client";
import formatDateTime from "@/utils/formatDateTime";

const badgeMap = {
  processing: "bg-success text-success-foreground",
  processed: "bg-secondary text-secondary-foreground",
  failed: "bg-error text-error-foreground",
};

const Analysis = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");

  const { data, isLoading, isError, error } = useQuery<DocumentSummary[]>({
    queryKey: ["documents"],
    queryFn: fetchDocuments,
  });

  const documents = useMemo(() => data ?? [], [data]);

  const filteredDocuments = useMemo(() => {
    if (!searchQuery.trim()) {
      return documents;
    }
    const lower = searchQuery.toLowerCase();
    return documents.filter((item) => {
      const stored = item.storedName?.toLowerCase() ?? "";
      return (
        item.originalName.toLowerCase().includes(lower) ||
        stored.includes(lower) ||
        item.id.toLowerCase().includes(lower)
      );
    });
  }, [documents, searchQuery]);

  const totalDocuments = documents.length;
  const completedDocuments = useMemo(
    () => documents.filter((item) => item.status === "processed").length,
    [documents],
  );
  const inProgressDocuments = useMemo(
    () => documents.filter((item) => item.status === "processing").length,
    [documents],
  );

  if (isLoading) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-background via-accent/30 to-background">
        <div className="text-sm text-muted-foreground">분석 데이터를 불러오는 중입니다...</div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-background via-accent/30 to-background">
        <div className="text-sm text-destructive">
          {(error as Error)?.message ?? "분석 데이터를 불러오지 못했습니다."}
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full overflow-y-auto bg-gradient-to-br from-background via-accent/30 to-background">
      <div className="container mx-auto flex-1 px-5 py-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold">문서 분석 현황</h2>
            <p className="text-sm text-muted-foreground mt-1">
              업로드된 문서의 처리 상태와 벤치마크 결과를 확인하세요.
            </p>
          </div>
        </div>

        <div className="mt-6 space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-border bg-card p-6">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground">총 문서</span>
                <FileText className="h-5 w-5 text-primary" />
              </div>
              <div className="text-3xl font-bold">{totalDocuments}</div>
            </div>
            <div className="rounded-xl border border-border bg-card p-6">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground">처리 완료</span>
                <FileBarChart className="h-5 w-5 text-secondary" />
              </div>
              <div className="text-3xl font-bold">{completedDocuments}</div>
            </div>
            <div className="rounded-xl border border-border bg-card p-6">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground">진행 중</span>
                <Timer className="h-5 w-5 text-success" />
              </div>
              <div className="text-3xl font-bold">{inProgressDocuments}</div>
            </div>
          </div>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="파일명, 저장 이름 또는 문서 ID로 검색..."
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              className="pl-10"
            />
          </div>

          <div className="overflow-hidden rounded-xl border border-border bg-card">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-border bg-muted/50">
                  <tr>
                    <th className="p-4 text-left text-sm font-semibold">파일명</th>
                    <th className="p-4 text-center text-sm font-semibold">상태</th>
                    <th className="p-4 text-center text-sm font-semibold">페이지</th>
                    <th className="p-4 text-center text-sm font-semibold">상세</th>
                    <th className="p-4 text-center text-sm font-semibold">벤치마크</th>
                    <th className="p-4 text-center text-sm font-semibold">업로드 일시</th>
                    <th className="p-4 text-center text-sm font-semibold">완료 일시</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDocuments.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-8 text-center text-sm text-muted-foreground">
                        검색 조건에 해당하는 문서가 없습니다.
                      </td>
                    </tr>
                  ) : (
                    filteredDocuments.map((item, index) => (
                      <tr
                        key={item.id}
                        className={`border-b border-border transition-colors hover:bg-muted/30 ${
                          index % 2 === 0 ? "bg-background" : "bg-muted/10"
                        }`}
                      >
                        <td className="max-w-xs p-4">
                          <p
                            className="truncate text-sm text-muted-foreground"
                            title={item.originalName}
                          >
                            {item.originalName}
                          </p>
                          <p
                            className="truncate text-xs text-muted-foreground"
                            title={item.storedName}
                          >
                            저장 이름: {item.storedName}
                          </p>
                          <p className="text-[11px] text-muted-foreground">ID: {item.id}</p>
                        </td>
                        <td className="p-4 text-center">
                          <Badge
                            variant="outline"
                            className={`py-1.5 capitalize ${badgeMap[item.status]}`}
                          >
                            {item.status}
                          </Badge>
                        </td>
                        <td className="p-4 text-center">
                          <Badge variant="outline">{item.pagesCount}</Badge>
                        </td>
                        <td className="p-4">
                          <div className="flex items-center justify-center gap-3">
                            {item.status === "failed" ? (
                              <span className="text-xs text-destructive">에러</span>
                            ) : item.status === "uploaded" ? (
                              <span className="text-xs text-muted-foreground">준비 중</span>
                            ) : (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => navigate(`/analysis/${item.id}`)}
                                className="flex items-center gap-2 hover:border-primary/60 hover:text-primary"
                              >
                                <Sparkles className="h-4 w-4" />
                                상세 보기
                              </Button>
                            )}
                          </div>
                        </td>
                        <td className="p-4 text-center">
                          {item.status === "failed" ? (
                            <span className="text-xs text-destructive">에러</span>
                          ) : item.benchmarkUrl ? (
                            <Button asChild size="sm" variant="outline" className="gap-2">
                              <Link to={item.benchmarkUrl} target="_blank" rel="noreferrer">
                                <LinkIcon className="h-4 w-4" />
                                보기
                              </Link>
                            </Button>
                          ) : (
                            <span className="text-xs text-muted-foreground">준비 중</span>
                          )}
                        </td>
                        {/* 업로드 시간 */}
                        <td className="p-4 text-center">{formatDateTime(item.uploadedAt)}</td>
                        {/* 완료 시간 */}
                        <td className="p-4 text-center">{formatDateTime(item.processedAt)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analysis;
