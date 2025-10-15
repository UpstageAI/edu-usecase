import { useState, useCallback } from "react";
import { Upload as UploadIcon, FileText, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadDocument, DocumentSummary, type UploadDocumentPayload } from "@/lib/api-client";
import { useApiKey } from "@/hooks/use-api-key";
import { Input } from "@/components/ui/input";

const Upload = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { apiKey, setApiKey } = useApiKey();
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const uploadMutation = useMutation<DocumentSummary, Error, UploadDocumentPayload>({
    mutationFn: uploadDocument,
    onSuccess: async (item) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["documents"] }),
        queryClient.invalidateQueries({ queryKey: ["analysis-items"] }),
      ]);

      toast.success("문서 업로드가 완료되었습니다");
      setFile(null);

      // if (item.status === "processed" || item.pagesCount > 0) {
      if (item.status === "processed") {
        navigate(`/analysis/${item.id}`);
      } else {
        navigate("/analysis");
      }
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const dropped = e.dataTransfer.files?.[0];
    if (dropped) {
      setFile(dropped);
    }
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
    }
    e.target.value = ""; // 같은 파일 재선택 허용
  };

  const clearFile = () => {
    setFile(null);
  };

  const handleProcess = () => {
    if (!file) {
      toast.error("파일을 먼저 업로드해주세요");
      return;
    }

    if (!apiKey) {
      toast.error("API 키를 입력해주세요");
      return;
    }

    uploadMutation.mutate({ file, apiKey });
  };

  return (
    <div className="flex h-full w-full overflow-y-auto bg-gradient-to-br from-background via-accent/30 to-background">
      <div className="container mx-auto flex-1 px-5 py-5">
        <div className="max-w-4xl mx-auto space-y-8">
          <div className="space-y-2">
            <h2 className="text-3xl font-bold">문서 업로드</h2>
            <p className="text-muted-foreground">
              분석할 문서를 업로드하고 Multi-Agent 시스템으로 처리하세요
            </p>
          </div>

          {/* Upload Area */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            className={`relative overflow-hidden rounded-2xl border-2 border-dashed transition-all ${
              isDragging
                ? "border-primary bg-primary/5"
                : "border-border hover:border-primary/50 bg-card"
            }`}
          >
            <div className="p-12 text-center space-y-6">
              <div className="flex justify-center">
                <div
                  className={`w-20 h-20 rounded-full flex items-center justify-center transition-all ${
                    isDragging
                      ? "bg-primary/20 scale-110"
                      : "bg-gradient-to-br from-primary/10 to-secondary/10"
                  }`}
                >
                  <UploadIcon className="w-10 h-10 text-primary" />
                </div>
              </div>

              <div className="space-y-2">
                <h3 className="text-xl font-semibold">
                  {isDragging ? "여기에 파일을 놓으세요" : "파일을 드래그하거나"}
                </h3>
                <p className="text-muted-foreground">PDF, DOCX, 이미지 파일 지원</p>
              </div>

              <div>
                <input
                  type="file"
                  id="file-input"
                  accept=".pdf,.docx,.doc,.png,.jpg,.jpeg"
                  onChange={handleFileInput}
                  className="hidden"
                />
                <label htmlFor="file-input">
                  <Button
                    size="lg"
                    className="bg-gradient-to-r from-primary to-secondary hover:opacity-90 transition-opacity cursor-pointer"
                    asChild
                  >
                    <span>파일 선택</span>
                  </Button>
                </label>
              </div>
            </div>
          </div>

          {/* File List */}
          {file && (
            <div className="space-y-4">
              <h3 className="font-semibold">업로드된 파일</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between p-4 rounded-lg bg-card border border-border hover:border-primary/50 transition-all">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary/10 to-secondary/10 flex items-center justify-center">
                      <FileText className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium">{file.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={clearFile}
                    className="hover:bg-destructive/10 hover:text-destructive"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>
          )}

          <div className="flex flex-col gap-2">
            <h3 className="font-semibold">OCR API Key 입력</h3>
            <Input
              id="api-key"
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="Solar Pro2 / Upstage API Key"
              className="min-w-0 flex-1"
              aria-label="OCR API Key"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-4">
            <Button variant="outline" size="lg" onClick={() => navigate("/")} className="flex-1">
              취소
            </Button>
            <Button
              size="lg"
              onClick={handleProcess}
              disabled={!file || uploadMutation.isPending}
              className="flex-1 bg-gradient-to-r from-primary to-secondary hover:opacity-90 transition-opacity"
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  처리 중...
                </>
              ) : (
                "문서 처리 시작"
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Upload;
