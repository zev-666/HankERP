"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ArrowLeft, Play, CheckCircle2, Clock, AlertCircle } from "lucide-react";

const OP_STATUS_STYLE: Record<string, { label: string; bg: string; text: string }> = {
  pending: { label: "待開始", bg: "bg-slate-100", text: "text-slate-500" },
  in_progress: { label: "進行中", bg: "bg-amber-100", text: "text-amber-700" },
  completed: { label: "已完成", bg: "bg-green-100", text: "text-green-700" },
};

export default function MesWorkOrderPage() {
  const params = useParams();
  const router = useRouter();
  const qc = useQueryClient();
  const woId = params.id as string;

  const [reportingOpId, setReportingOpId] = useState<string | null>(null);
  const [goodQty, setGoodQty] = useState("");
  const [scrapQty, setScrapQty] = useState("");

  const { data: woResp, isLoading, isError } = useQuery({
    queryKey: ["mes-wo-detail", woId],
    queryFn: () => api.getWoDetail(woId),
    refetchInterval: 10000,
  });

  const startMut = useMutation({
    mutationFn: (opId: string) => api.startOp(woId, opId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mes-wo-detail", woId] }),
  });

  const completeMut = useMutation({
    mutationFn: () => api.completeOp(woId, reportingOpId!, Number(goodQty) || 0, Number(scrapQty) || 0),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mes-wo-detail", woId] });
      setReportingOpId(null);
      setGoodQty("");
      setScrapQty("");
    },
  });

  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-400 text-lg">載入中...</div>;
  }
  if (isError || !woResp?.data) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <AlertCircle size={40} className="text-red-400" />
        <div className="text-slate-600 text-lg">找不到工單，請確認編號</div>
        <button onClick={() => router.push("/mes")} className="bg-slate-900 text-white px-6 py-3 rounded-xl">
          返回掃描頁面
        </button>
      </div>
    );
  }

  const wo = woResp.data;

  return (
    <div className="min-h-screen flex flex-col">
      <div className="bg-slate-900 text-white px-6 py-5 flex items-center gap-4">
        <button onClick={() => router.push("/mes")} className="text-slate-300">
          <ArrowLeft size={24} />
        </button>
        <div>
          <div className="text-xl font-mono font-semibold">{wo.wo_number}</div>
          <div className="text-slate-400 text-sm">{wo.quantity} 台 ｜ 優先度 P{wo.priority}</div>
        </div>
      </div>

      <div className="p-6 space-y-4 flex-1">
        {wo.operations.map((op: any) => {
          const style = OP_STATUS_STYLE[op.status] || OP_STATUS_STYLE.pending;
          return (
            <div key={op.id} className="bg-white rounded-2xl border-2 border-slate-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-xs text-slate-400">工序 {op.op_seq}</div>
                  <div className="text-xl font-semibold text-slate-800">{op.op_name}</div>
                </div>
                <span className={`text-sm px-3 py-1.5 rounded-full font-medium ${style.bg} ${style.text}`}>
                  {style.label}
                </span>
              </div>

              {op.status === "completed" && (
                <div className="flex gap-4 text-sm text-slate-500">
                  <span>良品 {op.good_qty}</span>
                  <span className="text-red-500">不良 {op.scrap_qty}</span>
                </div>
              )}

              {op.status === "pending" && (
                <button
                  onClick={() => startMut.mutate(op.id)}
                  disabled={startMut.isPending}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-lg font-medium py-4 rounded-xl flex items-center justify-center gap-2"
                >
                  <Play size={20} /> 開始此工序
                </button>
              )}

              {op.status === "in_progress" && reportingOpId !== op.id && (
                <button
                  onClick={() => setReportingOpId(op.id)}
                  className="w-full bg-green-600 hover:bg-green-700 text-white text-lg font-medium py-4 rounded-xl flex items-center justify-center gap-2"
                >
                  <CheckCircle2 size={20} /> 完成並回報數量
                </button>
              )}

              {reportingOpId === op.id && (
                <div className="space-y-3 mt-2 border-t border-slate-100 pt-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm text-slate-500 mb-1">良品數量</label>
                      <input
                        type="number"
                        inputMode="numeric"
                        autoFocus
                        value={goodQty}
                        onChange={e => setGoodQty(e.target.value)}
                        className="w-full border-2 border-slate-300 rounded-xl px-4 py-3 text-2xl text-center font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-red-400 mb-1">不良品數量</label>
                      <input
                        type="number"
                        inputMode="numeric"
                        value={scrapQty}
                        onChange={e => setScrapQty(e.target.value)}
                        className="w-full border-2 border-red-200 rounded-xl px-4 py-3 text-2xl text-center font-mono"
                      />
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <button onClick={() => setReportingOpId(null)} className="flex-1 border-2 border-slate-300 text-slate-600 py-3 rounded-xl text-lg">
                      取消
                    </button>
                    <button
                      onClick={() => completeMut.mutate()}
                      disabled={completeMut.isPending || !goodQty}
                      className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-green-300 text-white py-3 rounded-xl text-lg font-medium"
                    >
                      {completeMut.isPending ? "送出中..." : "確認完成"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {wo.operations.length === 0 && (
          <div className="text-center py-16 text-slate-400 text-lg flex flex-col items-center gap-2">
            <Clock size={32} className="opacity-40" />
            此工單尚未設定工序
          </div>
        )}
      </div>
    </div>
  );
}
