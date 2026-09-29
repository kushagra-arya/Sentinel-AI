"use client";

import { useEffect, useRef } from "react";

type ChartOption = {
  tooltip?: object;
  grid?: object;
  xAxis?: object;
  yAxis?: object;
  series?: object[];
  color?: string[];
  legend?: object;
};

export function ChartPanel({
  title,
  description,
  option
}: Readonly<{
  title: string;
  description: string;
  option: ChartOption;
}>) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let chart: import("echarts").ECharts | null = null;
    const resize = () => chart?.resize();
    void import("echarts").then((echarts) => {
      if (!ref.current) {
        return;
      }
      chart = echarts.init(ref.current, "dark");
      chart.setOption(option);
      window.addEventListener("resize", resize);
      resize();
    });
    return () => {
      window.removeEventListener("resize", resize);
      chart?.dispose();
    };
  }, [option]);

  return (
    <section className="rounded-md border border-border bg-card">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold">{title}</h2>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <div ref={ref} className="h-64 w-full" />
    </section>
  );
}
