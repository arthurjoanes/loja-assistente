import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const productFont = localFont({
  src: "./fonts/source-sans-3.woff2",
  weight: "200 900",
  variable: "--font-product",
  display: "swap",
  fallback: ["Arial"],
});

export const metadata: Metadata = {
  title: "Loja Assistente · Vendas",
  description: "Consulta de vendas por loja e período, com dados fictícios.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" className={productFont.variable}>
      <body>{children}</body>
    </html>
  );
}
