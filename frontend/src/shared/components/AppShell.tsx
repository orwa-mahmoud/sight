import {
  ActionIcon,
  Avatar,
  Box,
  Group,
  AppShell as MantineAppShell,
  NavLink,
  ScrollArea,
  Stack,
  Text,
  Tooltip,
} from "@mantine/core";
import {
  IconBuildingStore,
  IconChartBar,
  IconFileText,
  IconLogout,
  IconMessageCircle,
  IconQuestionMark,
  IconSettings,
  IconShieldLock,
  IconUserPlus,
  IconUsers,
} from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation } from "react-router-dom";

import { useAuth } from "@auth/useAuth";
import { ColorSchemeToggle } from "@shared/components/ColorSchemeToggle";
import { IngestionProgress } from "@shared/components/IngestionProgress";
import { LanguageSwitcher } from "@shared/components/LanguageSwitcher";

type NavItem = { labelKey: string; to: string; icon: ReactNode; ownerOnly?: boolean };

const NAV_ITEMS: NavItem[] = [
  { labelKey: "nav.inbox", to: "/", icon: <IconQuestionMark size={18} stroke={1.6} /> },
  { labelKey: "nav.chatTest", to: "/chat", icon: <IconMessageCircle size={18} stroke={1.6} /> },
  { labelKey: "nav.conversations", to: "/conversations", icon: <IconMessageCircle size={18} stroke={1.6} /> },
  { labelKey: "nav.documents", to: "/documents", icon: <IconFileText size={18} stroke={1.6} /> },
  { labelKey: "nav.usage", to: "/usage", icon: <IconChartBar size={18} stroke={1.6} /> },
  { labelKey: "nav.team", to: "/team", icon: <IconUserPlus size={18} stroke={1.6} />, ownerOnly: true },
  { labelKey: "nav.settings", to: "/settings", icon: <IconSettings size={18} stroke={1.6} />, ownerOnly: true },
];

// Platform-admin-only nav items, appended below a divider for admins.
const ADMIN_NAV_ITEMS: Array<{ labelKey: string; to: string; icon: ReactNode }> = [
  { labelKey: "nav.adminTenants", to: "/admin/tenants", icon: <IconBuildingStore size={18} stroke={1.6} /> },
  { labelKey: "nav.adminUsers", to: "/admin/users", icon: <IconUsers size={18} stroke={1.6} /> },
];

export function ProtectedShell({ children }: Readonly<{ children: ReactNode }>) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const { t } = useTranslation();

  return (
    <MantineAppShell header={{ height: 56 }} navbar={{ width: 240, breakpoint: "sm" }} padding="lg">
      <a
        href="#main-content"
        style={{
          position: "absolute",
          left: -9999,
          top: "auto",
          width: 1,
          height: 1,
          overflow: "hidden",
        }}
        onFocus={(e) => {
          e.currentTarget.style.position = "fixed";
          e.currentTarget.style.left = "8px";
          e.currentTarget.style.top = "8px";
          e.currentTarget.style.width = "auto";
          e.currentTarget.style.height = "auto";
          e.currentTarget.style.zIndex = "9999";
        }}
        onBlur={(e) => {
          e.currentTarget.style.position = "absolute";
          e.currentTarget.style.left = "-9999px";
        }}
      >
        {t("common.skipToContent")}
      </a>
      <MantineAppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="xs">
            <Box
              role="img"
              aria-label="Sight logo"
              style={{
                width: 30,
                height: 30,
                borderRadius: 8,
                background:
                  "linear-gradient(135deg, var(--mantine-color-coral-5), var(--mantine-color-coral-7))",
              }}
            />
            <Text fw={700} size="lg">
              Sight
            </Text>
          </Group>
          <Group gap="sm">
            <Group gap="xs">
              <Avatar color="coral" radius="xl" size="sm">
                {(user?.full_name ?? user?.email ?? "?")[0]?.toUpperCase()}
              </Avatar>
              <Box visibleFrom="sm">
                <Text size="sm" fw={500} lh={1}>
                  {user?.full_name ?? user?.email}
                </Text>
                <Text size="xs" c="dimmed">
                  {user?.tenant.name}
                </Text>
              </Box>
            </Group>
            <LanguageSwitcher />
            <ColorSchemeToggle />
            <Tooltip label={t("common.signOut")}>
              <ActionIcon variant="subtle" color="gray" onClick={logout} aria-label={t("common.signOut")}>
                <IconLogout size={18} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>
      </MantineAppShell.Header>

      <MantineAppShell.Navbar p="sm">
        <ScrollArea h="100%">
          <Stack gap={2}>
            {NAV_ITEMS.filter((item) => !item.ownerOnly || user?.tenant.role === "owner").map((item) => (
              <NavLink
                key={item.to}
                component={Link}
                to={item.to}
                label={t(item.labelKey)}
                leftSection={item.icon}
                active={item.to === "/" ? location.pathname === "/" : location.pathname.startsWith(item.to)}
              />
            ))}
          </Stack>

          {user?.is_platform_admin && (
            <Stack gap={2} mt="md">
              <Group gap={6} px="sm" mb={4} c="dimmed">
                <IconShieldLock size={14} stroke={1.6} />
                <Text size="xs" fw={600} tt="uppercase">
                  {t("nav.adminSection")}
                </Text>
              </Group>
              {ADMIN_NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.to}
                  component={Link}
                  to={item.to}
                  label={t(item.labelKey)}
                  leftSection={item.icon}
                  active={location.pathname.startsWith(item.to)}
                />
              ))}
            </Stack>
          )}
          <Box mt="lg">
            <NavLink
              component="div"
              label={user?.tenant.slug ?? ""}
              description={user?.tenant.role ?? ""}
              leftSection={<IconBuildingStore size={18} stroke={1.6} />}
              variant="subtle"
              styles={{ root: { borderRadius: 6 } }}
            />
          </Box>
        </ScrollArea>
      </MantineAppShell.Navbar>

      {/* tabIndex=-1 so the skip link moves keyboard focus here, not just scroll. */}
      <MantineAppShell.Main id="main-content" tabIndex={-1}>
        {children}
      </MantineAppShell.Main>

      {/* Global, non-blocking ingestion progress — visible from any page, backed
          by the server so it survives a refresh. */}
      <IngestionProgress />
    </MantineAppShell>
  );
}
