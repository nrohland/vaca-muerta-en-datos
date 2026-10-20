"use client";
import { createContext, useContext, useMemo, type ReactNode } from "react";
import { formatters, type Language } from "./i18n";
const LocaleContext = createContext(formatters("es"));
export function LocaleProvider({
  language,
  children,
}: {
  language: Language;
  children: ReactNode;
}) {
  const value=useMemo(()=>formatters(language),[language]);
  return (
    <LocaleContext.Provider value={value}>
      {children}
    </LocaleContext.Provider>
  );
}
export const useLocale = () => useContext(LocaleContext);
