"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Plus, Trash2, CheckCircle, Layers, Package } from "lucide-react";

interface BomItemForm {
  material_id: string;
  material_label: string;
  quantity: number;
  unit: string;
  wastage_rate: number;
  cut_length_mm?: number;
  cut_width_mm?: number;
}

export default function ProductsBomPage() {
  const qc = useQueryClient();
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [showCreateProduct, setShowCreateProduct] = useState(false);
  const [showBomEditor, setShowBomEditor] = useState(false);
  const [expandResult, setExpandResult] = useState<any>(null);

  const [productForm, setProductForm] = useState({ sku: "", name: "", category: "彩妝展示架", product_type: "custom" });
  const [bomItems, setBomItems] = useState<BomItemForm[]>([
    { material_id: "", material_label: "透明壓克力 3mm", quantity: 2, unit: "片", wastage_rate: 0.05, cut_length_mm: 500, cut_width_mm: 400 },
  ]);

  const { data: products } = useQuery({ queryKey: ["products"], queryFn: () => api.getProducts() });
  const { data: materials } = useQuery({ queryKey: ["materials"], queryFn: () => api.getMaterials() });
  const { data: bom, refetch: refetchBom } = useQuery({
    queryKey: ["bom", selectedProductId],
    queryFn: () => api.getBom(selectedProductId),
    enabled: !!selectedProductId,
    retry: false,
  });

  const createProductMut = useMutation({
    mutationFn: (d: any) => api.createProduct(d),
    onSuccess: (res: any) => {
      qc.invalidateQueries({ queryKey: ["products"] });
      setShowCreateProduct(false);
      setSelectedProductId(res.product_id);
    },
  });

  const createBomMut = useMutation({
    mutationFn: () => api.createBom({
      product_id: selectedProductId,
      version: 1,
      items: bomItems.map((it, i) => ({
        line_no: i + 1,
        material_id: it.material_id,
        quantity: it.quantity,
        unit: it.unit,
        wastage_rate: it.wastage_rate,
        cut_length_mm: it.cut_length_mm,
        cut_width_mm: it.cut_width_mm,
      })),
    }),
    onSuccess: () => {
      setShowBomEditor(false);
      refetchBom();
    },
  });

  const approveMut = useMutation({
    mutationFn: (bomId: string) => api.approveBom(bomId),
    onSuccess: () => refetchBom(),
  });

  const expandMut = useMutation({
    mutationFn: (bomId: string) => api.expandBom(bomId),
    onSuccess: (data: any) => setExpandResult(data),
  });

  const addBomItem = () => setBomItems(p => [...p, {
    material_id: "", material_label: "", quantity: 1, unit: "片", wastage_rate: 0.05,
  }]);
  const removeBomItem = (i: number) => setBomItems(p => p.filter((_, idx) => idx !== i));
  const updateBomItem = (i: number, field: keyof BomItemForm, value: any) =>
    setBomItems(p => p.map((it, idx) => idx === i ? { ...it, [field]: value } : it));

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-800">產品 / BOM 管理</h1>
        <button onClick={() => setShowCreateProduct(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          + 新增產品
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Product List */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2 text-sm font-medium text-slate-700">
            <Package size={14} /> 產品清單
          </div>
          <div className="divide-y divide-slate-50 max-h-[600px] overflow-y-auto">
            {(products?.data || []).map((p: any) => (
              <button key={p.id} onClick={() => { setSelectedProductId(p.id); setExpandResult(null); }}
                className={`w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors ${selectedProductId === p.id ? "bg-blue-50 border-l-2 border-blue-600" : ""}`}>
                <div className="text-sm font-medium text-slate-800">{p.name}</div>
                <div className="text-xs text-slate-400 font-mono mt-0.5">{p.sku}</div>
              </button>
            ))}
            {(!products?.data || products.data.length === 0) && (
              <div className="text-center py-10 text-slate-400 text-sm">尚無產品資料</div>
            )}
          </div>
        </div>

        {/* BOM Detail */}
        <div className="lg:col-span-2 space-y-4">
          {!selectedProductId && (
            <div className="bg-white rounded-xl border border-slate-200 p-10 text-center text-slate-400">
              <Layers size={32} className="mx-auto mb-2 opacity-30" />
              請從左側選擇產品以查看或建立 BOM
            </div>
          )}

          {selectedProductId && !bom?.data && (
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
              <p className="text-slate-500 text-sm mb-4">此產品尚未建立 BOM</p>
              <button onClick={() => setShowBomEditor(true)}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
                建立 BOM
              </button>
            </div>
          )}

          {selectedProductId && bom?.data && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-700">BOM v{bom.data.version}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${bom.data.status === "active" ? "bg-green-100 text-green-600" : "bg-amber-100 text-amber-600"}`}>
                    {bom.data.status === "active" ? "已發佈" : "草稿"}
                  </span>
                </div>
                <div className="flex gap-2">
                  {bom.data.status !== "active" && (
                    <button onClick={() => approveMut.mutate(bom.data.id)}
                      className="flex items-center gap-1 text-xs text-green-600 hover:text-green-700">
                      <CheckCircle size={13} /> 審核發佈
                    </button>
                  )}
                  <button onClick={() => expandMut.mutate(bom.data.id)}
                    className="text-xs text-blue-600 hover:text-blue-700">
                    展開計算成本
                  </button>
                </div>
              </div>

              {expandResult?.items && (
                <div className="mb-4 bg-slate-50 rounded-lg p-4">
                  <div className="text-xs font-medium text-slate-600 mb-3">BOM 展開結果（含損耗計算）</div>
                  <table className="w-full text-xs">
                    <thead><tr className="text-slate-400">
                      <th className="text-left py-1.5">材料</th>
                      <th className="text-right py-1.5">需求量</th>
                      <th className="text-right py-1.5">含損耗量</th>
                      <th className="text-right py-1.5">成本</th>
                    </tr></thead>
                    <tbody>
                      {expandResult.items.map((it: any, i: number) => (
                        <tr key={i} className="border-t border-slate-100">
                          <td className="py-1.5 text-slate-700">{it.material_name}</td>
                          <td className="py-1.5 text-right">{it.quantity} {it.unit}</td>
                          <td className="py-1.5 text-right text-amber-600">{it.quantity_with_waste} {it.unit}</td>
                          <td className="py-1.5 text-right font-medium">NT$ {it.line_cost.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="flex justify-end mt-2 pt-2 border-t border-slate-200">
                    <span className="text-sm font-semibold text-slate-800">
                      總材料成本：NT$ {expandResult.total_material_cost.toLocaleString()}
                    </span>
                  </div>
                </div>
              )}

              <div className="text-xs text-slate-400">
                建立日期：{bom.data.created_at ? new Date(bom.data.created_at).toLocaleDateString("zh-TW") : "—"}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Product Modal */}
      {showCreateProduct && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-4">新增產品</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">SKU</label>
                <input value={productForm.sku} onChange={e => setProductForm(f => ({ ...f, sku: e.target.value }))}
                  placeholder="例如：COS-A001" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">產品名稱</label>
                <input value={productForm.name} onChange={e => setProductForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">類別</label>
                <select value={productForm.category} onChange={e => setProductForm(f => ({ ...f, category: e.target.value }))}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
                  <option>彩妝展示架</option><option>酒類展示櫃</option><option>家電展示架</option>
                  <option>尿布展示架</option><option>客製化展示櫃</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowCreateProduct(false)} className="flex-1 border border-slate-300 text-slate-600 py-2 rounded-lg text-sm">取消</button>
              <button onClick={() => createProductMut.mutate(productForm)} disabled={createProductMut.isPending || !productForm.sku || !productForm.name}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 disabled:bg-blue-300">
                {createProductMut.isPending ? "建立中..." : "確認新增"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* BOM Editor Modal */}
      {showBomEditor && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">建立 BOM</h2>
              <button onClick={addBomItem} className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700">
                <Plus size={13} /> 新增材料項
              </button>
            </div>
            <div className="space-y-3">
              {bomItems.map((it, i) => (
                <div key={i} className="border border-slate-200 rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-500">材料項 {i + 1}</span>
                    <button onClick={() => removeBomItem(i)} className="text-slate-400 hover:text-red-500">
                      <Trash2 size={13} />
                    </button>
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">物料ID（從物料主檔複製UUID）</label>
                    <input value={it.material_id} onChange={e => updateBomItem(i, "material_id", e.target.value)}
                      placeholder="material UUID" className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs font-mono" />
                  </div>
                  <div className="grid grid-cols-4 gap-2">
                    <div>
                      <label className="text-[10px] text-slate-400">數量</label>
                      <input type="number" value={it.quantity} onChange={e => updateBomItem(i, "quantity", +e.target.value)}
                        className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs" />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400">單位</label>
                      <input value={it.unit} onChange={e => updateBomItem(i, "unit", e.target.value)}
                        className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs" />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400">損耗率</label>
                      <input type="number" step="0.01" value={it.wastage_rate} onChange={e => updateBomItem(i, "wastage_rate", +e.target.value)}
                        className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs" />
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-400">裁切長x寬(mm)</label>
                      <div className="flex gap-1">
                        <input type="number" value={it.cut_length_mm || ""} onChange={e => updateBomItem(i, "cut_length_mm", +e.target.value)}
                          className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs" />
                        <input type="number" value={it.cut_width_mm || ""} onChange={e => updateBomItem(i, "cut_width_mm", +e.target.value)}
                          className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs" />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowBomEditor(false)} className="flex-1 border border-slate-300 text-slate-600 py-2 rounded-lg text-sm">取消</button>
              <button onClick={() => createBomMut.mutate()} disabled={createBomMut.isPending}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 disabled:bg-blue-300">
                {createBomMut.isPending ? "建立中..." : "建立 BOM"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
