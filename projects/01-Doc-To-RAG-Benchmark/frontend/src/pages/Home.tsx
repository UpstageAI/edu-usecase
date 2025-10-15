import { Upload, FileText, Bot, FileBarChart } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";

const Home = () => {
  const navigate = useNavigate();

  return (
    <div className="flex h-full w-full overflow-y-auto bg-gradient-to-br from-background via-accent/30 to-background">
      <section className="container mx-auto flex-1 px-5 py-5">
        <div className="max-w-4xl mx-auto text-center flex flex-col gap-8">
          <div className="space-y-4">
            <h2 className="text-5xl font-bold tracking-tight leading-tight">
              Multi-Agent 기반
              <br />
              <span className="bg-gradient-to-r from-primary via-secondary to-primary-glow bg-clip-text text-transparent">
                문서 처리 자동화
              </span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Planner, Judge, Parsing, Refiner, Reporter로 구성된
              <br />
              Multi-Agent 구조로 문서 분석을 자동화합니다
            </p>
          </div>

          {/* Upload Area */}
          <div>
            <div
              onClick={() => navigate("/upload")}
              className="group relative overflow-hidden rounded-2xl border-2 border-dashed border-border hover:border-primary transition-all cursor-pointer bg-card p-12 hover:shadow-[0_0_40px_-10px_hsl(var(--primary)/0.3)]"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-secondary/5 opacity-0 group-hover:opacity-100 transition-opacity" />

              <div className="relative space-y-6">
                <div className="flex justify-center">
                  <div className="w-20 h-20 rounded-full bg-gradient-to-br from-primary/10 to-secondary/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                    <Upload className="w-10 h-10 text-primary" />
                  </div>
                </div>

                <div className="space-y-2">
                  <h3 className="text-2xl font-semibold">문서 업로드</h3>
                </div>

                <Button
                  size="lg"
                  className="bg-gradient-to-r from-primary to-secondary hover:opacity-90 transition-opacity"
                >
                  시작하기
                </Button>
              </div>
            </div>
          </div>

          {/* Features */}
          <div className="grid md:grid-cols-3 gap-6">
            <div className="flex flex-col items-center group p-6 rounded-xl bg-card border border-border hover:border-primary/50 transition-all hover:shadow-[var(--shadow-card)]">
              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary/10 to-secondary/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <FileText className="w-6 h-6 text-primary" />
              </div>
              <h3 className="font-semibold mb-2">OCR 분석</h3>
              <p className="text-sm text-muted-foreground">
                고정밀 OCR로 문서의 텍스트를 정확하게 추출합니다
              </p>
            </div>

            <div className="flex flex-col items-center group p-6 rounded-xl bg-card border border-border hover:border-primary/50 transition-all hover:shadow-[var(--shadow-card)]">
              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary/10 to-secondary/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <Bot className="w-6 h-6 text-primary" />
              </div>
              <h3 className="font-semibold mb-2">AI 챗봇</h3>
              <p className="text-sm text-muted-foreground">
                LLM이 자동으로 질문과 답변을 생성합니다
              </p>
            </div>

            <div className="flex flex-col items-center group p-6 rounded-xl bg-card border border-border hover:border-primary/50 transition-all hover:shadow-[var(--shadow-card)]">
              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-primary/10 to-secondary/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <FileBarChart className="w-6 h-6 text-primary" />
              </div>
              <h3 className="font-semibold mb-2">리포트 생성</h3>
              <p className="text-sm text-muted-foreground">
                분석 결과를 종합하여 상세 리포트를 제공합니다
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Home;
