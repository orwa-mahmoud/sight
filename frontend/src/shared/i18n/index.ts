import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import ar from "./locales/ar/common.json";
import en from "./locales/en/common.json";

export const SUPPORTED_LANGUAGES = ["en", "ar"] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];

const RTL_LANGUAGES = new Set<string>(["ar"]);

/** Text direction for a language code. */
export function dirFor(language: string): "ltr" | "rtl" {
  return RTL_LANGUAGES.has(language) ? "rtl" : "ltr";
}

// Resources are bundled (not fetched), so init is synchronous — `t()` returns
// real strings on first render, in the app and in tests alike.
i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { common: en },
      ar: { common: ar },
    },
    fallbackLng: "en",
    defaultNS: "common",
    supportedLngs: SUPPORTED_LANGUAGES,
    // Collapse region codes ("en-US" → "en") so resolvedLanguage is always one
    // of SUPPORTED_LANGUAGES.
    load: "languageOnly",
    nonExplicitSupportedLngs: true,
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "sight_lang",
    },
  });

export default i18n;
