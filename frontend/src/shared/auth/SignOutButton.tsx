// AI contribution: 50% or more AI-generated
import { ActionIcon, Menu, Text } from "@mantine/core";
import { IconLogout } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { useAuth } from "./authContext";

/** Shared sign-out action for public, mobile and staff layouts. */
export function SignOutButton({ menu = false }: { menu?: boolean }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { signOut } = useAuth();
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  async function onSignOut() {
    setPending(true);
    setFailed(false);
    try {
      await signOut();
      navigate("/sign-in", { replace: true });
    } catch {
      setFailed(true);
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      {menu ? (
        <Menu.Item
          closeMenuOnClick={false}
          leftSection={<IconLogout size={18} stroke={2} aria-hidden />}
          disabled={pending}
          onClick={() => void onSignOut()}
        >
          {t("auth.common.signOut")}
        </Menu.Item>
      ) : (
        <ActionIcon
          variant="subtle"
          size={48}
          aria-label={t("auth.common.signOut")}
          disabled={pending}
          onClick={() => void onSignOut()}
        >
          <IconLogout size={20} stroke={2} aria-hidden />
        </ActionIcon>
      )}
      {failed && (
        <Text role="alert" size="xs" c="red">
          {t("auth.login.signOutError")}
        </Text>
      )}
    </>
  );
}
