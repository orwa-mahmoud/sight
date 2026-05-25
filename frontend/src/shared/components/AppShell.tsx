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
} from "@tabler/icons-react";
import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

import { useAuth } from "../../auth/useAuth";

const NAV_ITEMS: Array<{ label: string; to: string; icon: ReactNode }> = [
  { label: "Inbox", to: "/", icon: <IconQuestionMark size={18} stroke={1.6} /> },
  { label: "Conversations", to: "/conversations", icon: <IconMessageCircle size={18} stroke={1.6} /> },
  { label: "Documents", to: "/documents", icon: <IconFileText size={18} stroke={1.6} /> },
  { label: "Usage & cost", to: "/usage", icon: <IconChartBar size={18} stroke={1.6} /> },
  { label: "Settings", to: "/settings", icon: <IconSettings size={18} stroke={1.6} /> },
];

export function ProtectedShell({ children }: Readonly<{ children: ReactNode }>) {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <MantineAppShell
      header={{ height: 56 }}
      navbar={{ width: 240, breakpoint: "sm" }}
      padding="lg"
    >
      <MantineAppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="xs">
            <Box
              style={{
                width: 30,
                height: 30,
                borderRadius: 8,
                background:
                  "linear-gradient(135deg, var(--mantine-color-coral-5), var(--mantine-color-coral-7))",
              }}
            />
            <Text fw={700} size="lg">
              frontdesk
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
            <Tooltip label="Sign out">
              <ActionIcon variant="subtle" color="gray" onClick={logout} aria-label="Sign out">
                <IconLogout size={18} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>
      </MantineAppShell.Header>

      <MantineAppShell.Navbar p="sm">
        <ScrollArea h="100%">
          <Stack gap={2}>
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                component={Link}
                to={item.to}
                label={item.label}
                leftSection={item.icon}
                active={
                  item.to === "/" ? location.pathname === "/" : location.pathname.startsWith(item.to)
                }
              />
            ))}
          </Stack>
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

      <MantineAppShell.Main>{children}</MantineAppShell.Main>
    </MantineAppShell>
  );
}
