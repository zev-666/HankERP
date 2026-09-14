"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid } from "recharts";
import { AlertTriangle, TrendingUp, Layers, Clock } from "lucide-react";

function KpiCard({ label, value, sub, color = "text-slate-800" }: any) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className={`text-2xl font-semibold ${color}`}>{value}</div>
      {sub && <div className="text-xs text-slate-400 mt-1">{sub}</div>}
    </div>
  );
}

export default function DashboardPage() {
  const { data: dash } = useQuery({ queryKey: ["dashboard"], queryFn: () => api.getDashboard() });
  const { data: util } = useQuery({ queryKey: ["utilization"], queryFn: () => api.getMaterialUtilization(6) });
  const { data: alerts } = useQuery({ queryKey: ["lowstock"], queryFn: () => api.getLowStock() });
  const { data: wos } = useQuery({ queryKey: ["wos-active"], queryFn: () => api.getWos("in_progress") });

  const kpi = dash?.kpi || {};

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-800">廠長儀表板</h1>
        <div className="text-sm text-slate-500">{dash?.period?.month}</div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="本月工單數" value={kpi.monthly_work_orders ?? "—"} sub="張工單" />
        <KpiCard
          label="板材利用率"
          value={kpi.avg_material_utilization_pct ? `${kpi.avg_material_utilization_pct}%` : "—"}
          color={kpi.avg_material_utilization_pct >= 85 ? "text-green-600" : "text-amber-500"}
        />
        <KpiCard
          label="工單準時率"
          value={kpi.on_time_delivery_rate_pct ? `${kpi.on_time_delivery_rate_pct}%` : "—"}
          color={kpi.on_time_delivery_rate_pct >= 90 ? "text-green-600" : "text-red-500"}
        />
        <KpiCard
          label="報價成交率"
          value={kpi.quote_win_rate_pct ? `${kpi.quote_win_rate_pct}%` : "—"}
          sub={`本月 ${kpi.monthly_quotes ?? 0} 份報價`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Utilization Chart */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <h2 className="text-sm font-medium text-slate-700 mb-4">板材利用率趨勢（6個月）</h2>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={util?.data || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis domain={[60, 100]} tick={{ fontSize: 11 }} unit="%" />
              <Tooltip formatter={(v: any) => [`${v}%`, "利用率"]} />
              <Line type="monotone" dataKey="avg_utilization_pct" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Low Stock Alerts */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <h2 className="text-sm font-medium text-slate-700 mb-4 flex items-center gap-2">
            <AlertTriangle size={14} className="text-amber-500" />
            庫存預警
          </h2>
          {alerts?.data?.length === 0 && (
            <div className="text-slate-400 text-sm text-center py-6">庫存充足，無預警</div>
          )}
          <div className="space-y-2">
            {(alerts?.data || []).map((a: any, i: number) => (
              <div key={i} className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-100">
                <div>
                  <div className="text-sm font-medium text-slate-700">{a.material_name}</div>
                  <div className="text-xs text-slate-500">現存 {a.on_hand} | 安全庫存 {a.min_stock_qty}</div>
                </div>
                <div className="text-red-600 font-semibold text-sm">缺 {a.shortage}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Active Work Orders */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <h2 className="text-sm font-medium text-slate-700 mb-4">進行中工單</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="text-left py-2 px-3 text-xs font-medium text-slate-500">工單編號</th>
                <th className="text-left py-2 px-3 text-xs font-medium text-slate-500">數量</th>
                <th className="text-left py-2 px-3 text-xs font-medium text-slate-500">優先度</th>
                <th className="text-left py-2 px-3 text-xs font-medium text-slate-500">預計完工</th>
                <th className="text-left py-2 px-3 text-xs font-medium text-slate-500">狀態</th>
              </tr>
            </thead>
            <tbody>
              {(wos?.data || []).map((wo: any) => (
                <tr key={wo.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="py-2.5 px-3 font-mono text-blue-600">{wo.wo_number}</td>
                  <td className="py-2.5 px-3">{wo.quantity} 台</td>
                  <td className="py-2.5 px-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${wo.priority <= 3 ? "bg-red-100 text-red-600" : wo.priority <= 6 ? "bg-amber-100 text-amber-600" : "bg-slate-100 text-slate-500"}`}>
                      P{wo.priority}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-slate-600">{wo.planned_end || "—"}</td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-600">進行中</span>
                  </td>
                </tr>
              ))}
              {(!wos?.data || wos.data.length === 0) && (
                <tr><td colSpan={5} className="text-center py-6 text-slate-400 text-sm">目前無進行中工單</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
