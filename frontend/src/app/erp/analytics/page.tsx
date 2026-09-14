"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

const COLORS = ["#3b82f6", "#10b981", "#f59e0b"];

export default function AnalyticsPage() {
  const { data: cost } = useQuery({ queryKey: ["cost"], queryFn: () => api.getCostBreakdown() });
  const d = cost?.data;

  const pieData = d ? [
    { name: "材料成本", value: d.material_cost },
    { name: "加工成本", value: d.processing_cost },
    { name: "管銷攤提", value: d.overhead_cost },
  ] : [];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold text-slate-800">成本分析</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="text-xs text-slate-500 mb-1">本月營收</div>
          <div className="text-2xl font-semibold text-slate-800">NT$ {(d?.total_revenue || 0).toLocaleString()}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="text-xs text-slate-500 mb-1">本月成本</div>
          <div className="text-2xl font-semibold text-slate-800">NT$ {(d?.total_cost || 0).toLocaleString()}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="text-xs text-slate-500 mb-1">毛利</div>
          <div className="text-2xl font-semibold text-green-600">NT$ {(d?.gross_profit || 0).toLocaleString()}</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="text-xs text-slate-500 mb-1">平均毛利率</div>
          <div className="text-2xl font-semibold text-slate-800">{d?.avg_margin_pct || 0}%</div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <h2 className="text-sm font-medium text-slate-700 mb-4">成本結構分解</h2>
        {pieData.some(p => p.value > 0) ? (
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={(e) => `${e.name} ${((e.percent || 0) * 100).toFixed(0)}%`}>
                {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(v: any) => `NT$ ${v.toLocaleString()}`} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-center py-16 text-slate-400 text-sm">本月尚無成交報價資料</div>
        )}
      </div>
    </div>
  );
}
