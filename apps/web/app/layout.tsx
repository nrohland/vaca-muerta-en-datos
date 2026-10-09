import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Vaca Muerta en datos",
  description:
    "Producción mensual de petróleo y gas de Vaca Muerta. Vista previa de agregados oficiales.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-AR">
      <body>{children}</body>
    </html>
  );
}
