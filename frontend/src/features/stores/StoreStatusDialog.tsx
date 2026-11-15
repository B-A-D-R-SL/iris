// AI contribution: 50% or more AI-generated
/**
 * Confirm a store deactivation (Figma W7.3, node 261:8057) or reactivation,
 * with a required reason kept in the audit log (BR-STORE-005). The reason box
 * is not in the Figma frame; it was added for both actions in the US-14
 * decisions (C2). Layout follows W7.3: 560 px, 28 px padding, title, store
 * name, "•" lines, then the actions on the left.
 */
import { Button, Group, Modal, Text } from "@mantine/core";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { TextField } from "../../shared/forms";
import { Notice } from "../../shared/ui";
import { StoreFailed, type StaffStore } from "./adminApi";
import classes from "./stores.module.css";

export const REASON_MAX_LENGTH = 500;
const KEY = "storeAdmin.dialog";

export interface StoreStatusDialogProps {
  mode: "deactivate" | "reactivate";
  store: StaffStore;
  pending: boolean;
  error: unknown;
  onClose: () => void;
  onConfirm: (reason: string) => void;
}

/** What happens next: the W7.3 lines, or the reactivation line. */
function Consequences({ mode, store }: Pick<StoreStatusDialogProps, "mode" | "store">) {
  const { t } = useTranslation();
  if (mode === "reactivate") {
    return (
      <ul className={classes.bullets}>
        <li>{t(`${KEY}.reactivateBody`)}</li>
      </ul>
    );
  }
  return (
    <ul className={classes.bullets}>
      <li>{t(`${KEY}.deactivateListings`, { count: store.open_listings })}</li>
      <li>{t(`${KEY}.deactivateHouseholds`, { count: store.households_to_notify })}</li>
      <li>{t(`${KEY}.deactivatePosting`)}</li>
    </ul>
  );
}

/** The reason error goes under the box; anything else in a notice. */
function splitError(error: unknown, fallback: string) {
  const reason = error instanceof StoreFailed ? error.fields.reason?.[0] : undefined;
  if (!error || reason) return { reason, other: null };
  return {
    reason,
    other: error instanceof StoreFailed && error.message ? error.message : fallback,
  };
}

const DIALOG_CLASSES = {
  content: classes.dialogContent,
  header: classes.dialogHeader,
  title: classes.dialogTitle,
  body: classes.dialogBody,
};

export function StoreStatusDialog(props: StoreStatusDialogProps) {
  const { mode, store, pending, error, onClose, onConfirm } = props;
  const { t } = useTranslation();
  const [reason, setReason] = useState("");
  const errors = splitError(error, t(`${KEY}.failed`));
  return (
    <Modal
      opened
      onClose={onClose}
      title={t(`${KEY}.${mode}Title`)}
      size={560}
      withCloseButton={false}
      classNames={DIALOG_CLASSES}
    >
      <Text className={classes.subtitle}>{store.name}</Text>
      <Consequences mode={mode} store={store} />
      <TextField
        label={t(`${KEY}.reason`)}
        description={t(`${KEY}.reasonHelp`)}
        value={reason}
        maxLength={REASON_MAX_LENGTH}
        multiline
        error={errors.reason}
        onChange={setReason}
      />
      {errors.other && <Notice type="error">{errors.other}</Notice>}
      <Group gap={12}>
        <Button
          color={mode === "deactivate" ? "danger" : undefined}
          loading={pending}
          disabled={!reason.trim()}
          onClick={() => onConfirm(reason.trim())}
        >
          {t(`${KEY}.${mode}`)}
        </Button>
        <Button variant="subtle" onClick={onClose}>
          {t(`${KEY}.back`)}
        </Button>
      </Group>
    </Modal>
  );
}
