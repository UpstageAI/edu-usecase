import { useState } from "react";
import { Button } from "@/components/ui/button";
import { TableCell, TableRow } from "@/components/ui/table";
import { useIsClamped } from "@/hooks/useClampled";

interface TextLineProps {
  line: string;
  index: number;
  pageNumber?: number;
}

export const TextLine = ({ line, index, pageNumber }: TextLineProps) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const rowKey = `${pageNumber ?? 0}-${index}`;

  const { ref, clamped } = useIsClamped<HTMLDivElement>([line, pageNumber]);

  return (
    <TableRow key={rowKey}>
      <TableCell className="text-center text-xs text-muted-foreground">{index + 1}</TableCell>

      <TableCell className="text-sm text-foreground">
        <div className="flex flex-col items-start justify-between gap-2">
          <div
            ref={ref}
            className={isExpanded ? "whitespace-pre-wrap" : "line-clamp-2 whitespace-pre-wrap"}
          >
            {line}
          </div>
          {(clamped || isExpanded) && (
            <Button
              variant="ghost"
              size="sm"
              className="shrink-0 h-6 px-2"
              onClick={() => setIsExpanded((prev) => !prev)}
              aria-expanded={isExpanded}
            >
              {isExpanded ? "간략히" : "더보기"}
            </Button>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
};
