// AI contribution: 50% or more AI-generated
/** The fields of one notice card: the five notice values, or a reason for not filing. */
import { Button, Checkbox, FileButton, Group, SimpleGrid, Stack } from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import { IconCamera } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import {
  DateField,
  FileUpload,
  IntegerField,
  MoneyField,
  PostalCodeField,
  TextField,
} from "../../../../shared/forms";
import {
  FIRST_TAX_YEAR,
  MAX_REASON,
  NOTICE_MAX_MB,
  NOTICE_TYPES,
  type NoticeValues,
} from "./noticeForm";
import classes from "./WalkIn.module.css";

type Form = UseFormReturnType<NoticeValues>;

/** Photograph the notice with the device camera (or choose a file below). */
function CameraButton({ form }: { form: Form }) {
  const { t } = useTranslation();
  return (
    <FileButton
      onChange={(file) => form.setFieldValue("file", file)}
      accept="image/*"
      capture="environment"
    >
      {(buttonProps) => (
        <Button
          {...buttonProps}
          className={classes.cameraButton}
          variant="outline"
          leftSection={<IconCamera size={18} aria-hidden />}
        >
          {t("staff.walkInNotices.takePhoto")}
        </Button>
      )}
    </FileButton>
  );
}

function FiledFields({ form, today }: { form: Form; today: string }) {
  const { t } = useTranslation();
  const lastYear = Number(today.slice(0, 4)) - 1;
  return (
    <>
      <Stack gap="xs">
        <CameraButton form={form} />
        <FileUpload
          {...form.getInputProps("file")}
          label={t("staff.walkInNotices.file")}
          accept={NOTICE_TYPES}
          maxMb={NOTICE_MAX_MB}
          buttonLabel={t("staff.walkInNotices.chooseFile")}
        />
      </Stack>
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        <IntegerField
          {...form.getInputProps("taxYear")}
          label={t("staff.walkInNotices.taxYear")}
          min={FIRST_TAX_YEAR}
          max={lastYear}
        />
        <MoneyField
          {...form.getInputProps("totalIncomeCents")}
          label={t("staff.walkInNotices.totalIncome")}
        />
        <TextField
          {...form.getInputProps("nameOnNotice")}
          label={t("staff.walkInNotices.nameOnNotice")}
          autoComplete="off"
        />
        <PostalCodeField
          {...form.getInputProps("postalCodeOnNotice")}
          label={t("staff.walkInNotices.postalCodeOnNotice")}
        />
        <DateField
          {...form.getInputProps("noticeDate")}
          label={t("staff.walkInNotices.noticeDate")}
          maxDate={today}
        />
      </SimpleGrid>
      <Checkbox
        {...form.getInputProps("seenInPerson", { type: "checkbox" })}
        size="md"
        label={t("staff.walkIn.noticeSeenInPerson")}
        description={t("staff.walkInNotices.seenHelp")}
      />
    </>
  );
}

interface NoticeFieldsProps {
  form: Form;
  today: string;
  locked: boolean;
  saving: boolean;
  /** A notice is already saved, so the form can be cancelled. */
  canCancel: boolean;
  onSave: () => void;
  onCancel: () => void;
}

export function NoticeFields({
  form,
  today,
  locked,
  saving,
  canCancel,
  onSave,
  onCancel,
}: NoticeFieldsProps) {
  const { t } = useTranslation();
  return (
    <Stack gap="md">
      <Checkbox
        {...form.getInputProps("didNotFile", { type: "checkbox" })}
        size="md"
        label={t("staff.walkInNotices.didNotFile")}
        description={t("staff.walkInNotices.didNotFileHelp")}
      />
      {form.values.didNotFile ? (
        <TextField
          {...form.getInputProps("reason")}
          label={t("staff.walkInNotices.reason")}
          multiline
          maxLength={MAX_REASON}
        />
      ) : (
        <FiledFields form={form} today={today} />
      )}
      <Group>
        <Button loading={saving} onClick={onSave} disabled={locked}>
          {t("staff.walkInNotices.save")}
        </Button>
        {canCancel && (
          <Button variant="subtle" onClick={onCancel} disabled={saving}>
            {t("staff.walkInNotices.cancel")}
          </Button>
        )}
      </Group>
    </Stack>
  );
}
