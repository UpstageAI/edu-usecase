import { useEffect, useId, useRef, useState } from "react";

type MermaidProps = {
  chart: string; // mermaid 코드
  theme?: "default" | "dark" | "neutral" | "forest";
  className?: string;
  securityLevel?: "strict" | "loose" | "antiscript" | "sandbox";
};

export default function Mermaid({
  chart,
  theme = "default",
  className,
  securityLevel = "strict",
}: MermaidProps) {
  const id = useId().replace(/:/g, "_");
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;

        mermaid.initialize({
          startOnLoad: false,
          theme,
          securityLevel,
        });

        const { svg } = await mermaid.render(`m_${id}`, chart);
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    })();

    return () => {
      cancelled = true;
      if (containerRef.current) containerRef.current.innerHTML = "";
    };
  }, [chart, theme, securityLevel, id]);

  return (
    <div className={className}>
      {error ? (
        <pre className="text-red-600 whitespace-pre-wrap">{error}</pre>
      ) : (
        <div ref={containerRef} aria-label="mermaid-graph" />
      )}
    </div>
  );
}
