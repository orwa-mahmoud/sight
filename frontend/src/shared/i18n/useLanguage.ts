import { useCallback } from "react";
import { useTranslation } from "react-i18next";

import { dirFor, type Language, SUPPORTED_LANGUAGES } from "@shared/i18n";

export interface UseLanguageReturn {
  language: Language;
  dir: "ltr" | "rtl";
  languages: readonly Language[];
  setLanguage: (language: Language) => void;
}

/** Read/switch the active language and its text direction. */
export function useLanguage(): UseLanguageReturn {
  const { i18n } = useTranslation();
  const language = (i18n.resolvedLanguage ?? "en") as Language;
  const setLanguage = useCallback(
    (next: Language) => {
      void i18n.changeLanguage(next);
    },
    [i18n]
  );
  return { language, dir: dirFor(language), languages: SUPPORTED_LANGUAGES, setLanguage };
}
