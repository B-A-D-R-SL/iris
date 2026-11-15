// AI contribution: 50% or more AI-generated
import { Button, Group, Modal, Stack, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";

const adminKey = "category.admin";

type DeactivateCategoryModalProps = {
  name: string;
  saving: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

/** Ask before deactivating a category (US-35 AC2: there is no delete). */
export function DeactivateCategoryModal({
  name,
  saving,
  onCancel,
  onConfirm,
}: DeactivateCategoryModalProps) {
  const { t } = useTranslation();
  return (
    <Modal opened onClose={onCancel} title={t(`${adminKey}.confirmTitle`, { name })}>
      <Stack gap="md">
        <Text>{t(`${adminKey}.confirmBody`)}</Text>
        <Group justify="flex-end" gap="sm">
          <Button variant="subtle" onClick={onCancel}>
            {t(`${adminKey}.cancel`)}
          </Button>
          <Button color="danger" loading={saving} onClick={onConfirm}>
            {t(`${adminKey}.deactivate`)}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
