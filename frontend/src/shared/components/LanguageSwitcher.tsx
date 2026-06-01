import { ActionIcon, Menu } from "@mantine/core";
import { IconLanguage } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import { type Language } from "@shared/i18n";
import { useLanguage } from "@shared/i18n/useLanguage";

const LABELS: Record<Language, string> = {
  en: "English",
  ar: "العربية",
};

export function LanguageSwitcher() {
  const { t } = useTranslation();
  const { language, languages, setLanguage } = useLanguage();

  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <ActionIcon variant="subtle" color="gray" aria-label={t("common.language")}>
          <IconLanguage size={18} />
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        {languages.map((lng) => (
          <Menu.Item
            key={lng}
            onClick={() => setLanguage(lng)}
            fw={lng === language ? 700 : 400}
          >
            {LABELS[lng]}
          </Menu.Item>
        ))}
      </Menu.Dropdown>
    </Menu>
  );
}
