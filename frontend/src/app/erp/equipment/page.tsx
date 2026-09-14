"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Cpu, Zap, Settings2 } from "lucide-react";

const TYPE_ICON: Record<string, any> = { cnc: Cpu, laser: Zap, default: Settings2 };
const STATUS_COLOR: Record<string, string> = {
  active: "bg-green-100 text-green-600", maintenance: "bg-amber-100 text-amber-600",
  breakdown: "bg-red-100 text-red-600", retired: "bg-slate-200 text-slate-400",
};

export default function EquipmentPage() {
  const { data: equipment } = useQuery({ queryKey: ["equipment"], queryFn: () => api.getEquipment() });

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold text-slate-800">設備管理</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {(equipment?.data || []).map((eq: any) => {
          const Icon = TYPE_ICON[eq.equipment_type] || TYPE_ICON.default;
          return (
            <div key={eq.id} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center"><Icon size={18} className="text-blue-600" /></div>
                <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${STATUS_COLOR[eq.status] || STATUS_COLOR.active}`}>{eq.status}</span>
              </div>
              <div className="font-medium text-slate-800">{eq.name}</div>
              <div className="text-xs text-slate-400 font-mono mt-0.5">{eq.code}</div>
              <div className="text-xs text-slate-500 mt-3">每小時成本：NT$ {eq.hourly_rate}</div>
            </div>
          );
        })}
        {(!equipment?.data || equipment.data.length === 0) && (
          <div className="col-span-3 text-center py-10 text-slate-400">尚無設備資料</div>
        )}
      </div>
    </div>
  );
}
