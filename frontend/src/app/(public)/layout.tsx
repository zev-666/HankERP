/**
 * 官網共用外框。.site 會套用 globals.css 裡的官網設計系統（深色、壓克力切邊輝光），
 * 範圍只限官網頁面，不會影響 /erp、/mes、/login。
 */
export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return <div className="site">{children}</div>;
}
