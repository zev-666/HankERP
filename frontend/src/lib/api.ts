const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("erp_token");
  }

  private async req<T>(path: string, opts: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const res = await fetch(`${BASE_URL}${path}`, {
      ...opts,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...opts.headers,
      },
    });
    if (res.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("erp_token");
        // token 過期時整頁重載回登入頁：同 store/auth.ts 的理由，
        // 這裡不在 React 渲染樹內，且我們要一併清空所有快取資料。
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        window.location.href = "/login";
      }
      throw new Error("未授權");
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({} as any));
      // detail 可能是字串，也可能是結構化物件（例如發料庫存不足時的缺料清單）。
      // 物件若直接丟進 Error 會變成 "[object Object]"，呼叫端就拿不到明細，
      // 因此序列化成 JSON 字串，讓呼叫端能自行 parse 後顯示細節。
      const detail = err?.detail;
      const message =
        typeof detail === "string"
          ? detail
          : detail != null
            ? JSON.stringify(detail)
            : `HTTP ${res.status}`;
      throw new Error(message);
    }
    return res.json();
  }

  get<T>(path: string) { return this.req<T>(path); }
  post<T>(path: string, body: unknown) {
    return this.req<T>(path, { method: "POST", body: JSON.stringify(body) });
  }
  patch<T>(path: string, body: unknown) {
    return this.req<T>(path, { method: "PATCH", body: JSON.stringify(body) });
  }

  // Auth
  login(email: string, password: string) {
    return this.post<{ access_token: string; token_type: string; user_id: string; user_name: string; role: string }>("/api/v1/auth/login", { email, password });
  }
  // Dashboard
  getDashboard() { return this.get<any>("/api/v1/analytics/dashboard"); }
  getMaterialUtilization(months = 6) { return this.get<any>(`/api/v1/analytics/material-utilization?months=${months}`); }
  getCostBreakdown() { return this.get<any>("/api/v1/analytics/cost-breakdown"); }
  getEquipmentOee() { return this.get<any>("/api/v1/analytics/equipment-oee"); }
  // Inventory
  getBalances(wh?: string) { return this.get<any>(`/api/v1/inventory/balance${wh ? `?warehouse_code=${wh}` : ""}`); }
  getSheets(remnant?: boolean) { return this.get<any>(`/api/v1/inventory/sheets${remnant !== undefined ? `?is_remnant=${remnant}` : ""}`); }
  getRemnants(minL = 0, minW = 0) { return this.get<any>(`/api/v1/inventory/remnants?min_length=${minL}&min_width=${minW}`); }
  receiveSheets(d: any) { return this.post("/api/v1/inventory/sheets/receive", d); }
  addRemnant(d: any) { return this.post("/api/v1/inventory/remnants", d); }
  getLowStock() { return this.get<any>("/api/v1/inventory/alerts/low-stock"); }
  // Nesting
  calculateNesting(d: any) { return this.post<any>("/api/v1/nesting/calculate", d); }
  getNestingJobs() { return this.get<any>("/api/v1/nesting/jobs"); }
  getNestingJob(id: string) { return this.get<any>(`/api/v1/nesting/jobs/${id}`); }
  // Quotations
  aiEstimate(d: any) { return this.post<any>("/api/v1/quotations/ai-estimate", d); }
  createQuotation(d: any) { return this.post<any>("/api/v1/quotations", d); }
  getQuotations() { return this.get<any>("/api/v1/quotations"); }
  updateQuoteStatus(id: string, status: string) { return this.patch(`/api/v1/quotations/${id}/status?status=${status}`, {}); }
  // Work Orders
  createWo(d: any) { return this.post<any>("/api/v1/work-orders", d); }
  getWos(status?: string) { return this.get<any>(`/api/v1/work-orders${status ? `?status=${status}` : ""}`); }
  getWoDetail(id: string) { return this.get<any>(`/api/v1/work-orders/${id}`); }
  releaseWo(id: string) { return this.post(`/api/v1/work-orders/${id}/release`, {}); }
  startOp(woId: string, opId: string) { return this.post(`/api/v1/work-orders/${woId}/operations/${opId}/start`, {}); }
  completeOp(woId: string, opId: string, goodQty: number, scrapQty: number) {
    return this.post(`/api/v1/work-orders/${woId}/operations/${opId}/complete`, { good_qty: goodQty, scrap_qty: scrapQty });
  }
  getMaterialPlan(woId: string) { return this.get<any>(`/api/v1/work-orders/${woId}/material-plan`); }
  // Customers
  getCustomers() { return this.get<any>("/api/v1/customers"); }
  createCustomer(d: any) { return this.post<any>("/api/v1/customers", d); }
  // Purchasing
  getPos() { return this.get<any>("/api/v1/purchase-orders"); }
  createPo(d: any) { return this.post<any>("/api/v1/purchase-orders", d); }
  // Equipment
  getEquipment() { return this.get<any>("/api/v1/equipment"); }
  // Products / BOM
  getProducts() { return this.get<any>("/api/v1/products"); }
  createProduct(d: any) { return this.post<any>("/api/v1/products", d); }
  getMaterials(type?: string, search?: string) {
    const params = new URLSearchParams();
    if (type) params.set("material_type", type);
    if (search) params.set("search", search);
    return this.get<any>(`/api/v1/materials?${params}`);
  }
  createMaterial(d: any) { return this.post<any>("/api/v1/materials", d); }
  getBom(productId: string, version?: number) {
    return this.get<any>(`/api/v1/products/${productId}/bom${version ? `?version=${version}` : ""}`);
  }
  createBom(d: any) { return this.post<any>("/api/v1/bom", d); }
  approveBom(bomId: string) { return this.post(`/api/v1/bom/${bomId}/approve`, {}); }
  expandBom(bomId: string) { return this.get<any>(`/api/v1/bom/${bomId}/expand`); }
  // Work Orders — 發料 / 完工入庫（v2.0新增，串接生產與庫存）
  issueWoMaterials(woId: string, warehouseCode = "RAW") {
    return this.post<any>(`/api/v1/work-orders/${woId}/issue-materials`, { warehouse_code: warehouseCode });
  }
  completeWo(woId: string, goodQty?: number, warehouseCode = "FG") {
    return this.post<any>(`/api/v1/work-orders/${woId}/complete`, {
      good_qty: goodQty ?? null, warehouse_code: warehouseCode,
    });
  }
  // Inquiries — 線上詢價（v2.0新增）
  getInquiries(status?: string) {
    return this.get<any>(`/api/v1/inquiries${status ? `?status=${status}` : ""}`);
  }
  getInquiry(id: string) { return this.get<any>(`/api/v1/inquiries/${id}`); }
  updateInquiryStatus(id: string, status: string, internalNotes?: string) {
    return this.patch<any>(`/api/v1/inquiries/${id}/status`, {
      status, internal_notes: internalNotes ?? null,
    });
  }
  convertInquiry(id: string) { return this.post<any>(`/api/v1/inquiries/${id}/convert-to-customer`, {}); }
  // Portfolio 後台（v2.0新增前端串接）
  getPortfolioCases() { return this.get<any>("/api/v1/portfolio"); }
  createPortfolioCase(d: any) { return this.post<any>("/api/v1/portfolio", d); }
  publishPortfolioCase(id: string) { return this.post<any>(`/api/v1/portfolio/${id}/publish`, {}); }
  // Quotation PDF
  getQuotePdfUrl(quoteId: string) {
    const token = this.getToken();
    return `${BASE_URL}/api/v1/quotations/${quoteId}/pdf`;
  }
}

export const api = new ApiClient();

