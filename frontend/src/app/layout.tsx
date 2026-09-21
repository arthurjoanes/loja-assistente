import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Loja Assistente · Vendas",
  description: "Consulta de vendas por loja e período, com dados fictícios.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
