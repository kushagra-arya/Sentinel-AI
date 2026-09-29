"use client";

import { motion } from "framer-motion";
import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";

import type { RiskLevel, RiskPrediction } from "@/lib/dashboard-types";
import { cn } from "@/lib/utils";

const riskStyles: Record<RiskLevel, string> = {
  low: "text-safe border-safe/40 bg-safe/5",
  medium: "text-informational border-informational/40 bg-informational/5",
  high: "text-warning border-warning/50 bg-warning/5",
  critical: "text-critical border-critical/50 bg-critical/5"
};

export function RiskScore({
  score,
  level,
  predictions
}: Readonly<{
  score: number;
  level: RiskLevel;
  predictions: RiskPrediction[];
}>) {
  const highestTrend = predictions.find((prediction) => prediction.minutes_to_high_risk !== null);
  const trend = highestTrend
    ? `Trending to high risk in ~${highestTrend.minutes_to_high_risk} min`
    : "No high-risk crossing forecast";
  const TrendIcon = highestTrend ? ArrowUpRight : score < 0.3 ? ArrowDownRight : ArrowRight;

  return (
    <section className={cn("rounded-md border p-5", riskStyles[level])} aria-label="Current plant risk">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.18em] text-muted-foreground">Current Plant Risk</p>
          <motion.div
            key={`${level}-${score}`}
            initial={{ opacity: 0.72 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.22 }}
            className="mt-3 text-6xl font-semibold leading-none"
          >
            {Math.round(score * 100)}
          </motion.div>
        </div>
        <div className="rounded-md border border-current px-3 py-2 text-sm font-semibold uppercase">
          {level}
        </div>
      </div>
      <div className="mt-5 flex items-center gap-2 text-sm">
        <TrendIcon className="h-4 w-4" aria-hidden="true" />
        <span>{trend}</span>
      </div>
    </section>
  );
}
