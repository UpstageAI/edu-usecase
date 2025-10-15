import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";

const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    console.error("404 Error: User attempted to access non-existent route:", location.pathname);
  }, [location.pathname]);

  return (
    <div className="flex h-full w-full items-center justify-center bg-background">
      <div className="rounded-xl border border-border bg-card px-10 py-12 text-center shadow-lg">
        <h1 className="text-5xl font-bold text-primary">404</h1>
        <p className="mt-4 text-lg text-muted-foreground">요청한 페이지를 찾을 수 없습니다.</p>
        <Link
          to="/"
          className="mt-6 inline-flex items-center justify-center rounded-lg bg-gradient-to-r from-primary to-secondary px-5 py-2 text-sm font-semibold text-white shadow-lg transition-opacity hover:opacity-90"
        >
          홈으로 돌아가기
        </Link>
      </div>
    </div>
  );
};

export default NotFound;
