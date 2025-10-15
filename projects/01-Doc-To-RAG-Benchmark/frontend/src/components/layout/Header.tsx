import { FileText } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";

const Header = () => {
  const navigate = useNavigate();

  return (
    <header className="border-b border-border/40 bg-card/60 backdrop-blur-md">
      <div className="container mx-auto flex items-center justify-between px-5 py-5">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate("/")}
          className="flex items-center gap-2 w-42 hover:bg-transparent"
        >
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-secondary">
            <FileText className="h-8 w-8 text-primary-foreground" />
          </span>
          <span className="text-2xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
            DocAgent
          </span>
        </Button>

        <div className="flex items-center gap-5">
          <div className="flex w-full max-w-md items-center justify-end gap-3 md:w-auto">
            <Button
              size="sm"
              className="bg-gradient-to-r from-primary to-secondary text-primary-foreground hover:opacity-90"
              onClick={() => navigate("/analysis")}
            >
              분석 현황
            </Button>
          </div>

          <div className="flex w-full max-w-md items-center justify-end gap-3 md:w-auto">
            <Button
              size="sm"
              className="bg-gradient-to-r from-primary to-secondary text-primary-foreground hover:opacity-90"
              onClick={() => navigate("/upload")}
            >
              문서 업로드
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
