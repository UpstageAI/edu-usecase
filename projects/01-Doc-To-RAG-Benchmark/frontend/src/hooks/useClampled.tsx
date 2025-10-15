import { useEffect, useRef, useState } from "react";

export function useIsClamped<T extends HTMLElement>(deps: unknown[] = []) {
  const ref = useRef<T | null>(null);
  const [clamped, setClamped] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const check = () => {
      // line-clamp-2가 적용된 상태에서 clientHeight < scrollHeight 이면 잘린 것
      setClamped(el.scrollHeight - el.clientHeight > 1);
    };

    // 초기 측정
    check();

    // 사이즈 변화를 추적 (리사이즈/폰트/열 너비 변화 등)
    const ro = new ResizeObserver(check);
    ro.observe(el);

    // 폰트 로딩 등 비동기 레이아웃 변화 대비
    const id = requestAnimationFrame(check);

    return () => {
      ro.disconnect();
      cancelAnimationFrame(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { ref, clamped };
}
