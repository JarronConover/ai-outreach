import * as React from "react";
import { cn } from "@/lib/utils";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "teal" | "green" | "gray";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        {
          "bg-[rgba(13,148,136,0.1)] text-[#0d9488]": variant === "teal" || variant === "default",
          "bg-green-100 text-green-700": variant === "green",
          "bg-gray-100 text-gray-600": variant === "gray",
        },
        className
      )}
      {...props}
    />
  );
}

export { Badge };
