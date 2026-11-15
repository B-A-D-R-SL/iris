// AI contribution: 50% or more AI-generated
/**
 * Edit, deactivate or reactivate a store (US-14, Figma W7.2 to W7.5).
 *
 * Save sends only the changed fields (PATCH). When the status switch changed,
 * a dialog asks for the reason first, then the page sends the PATCH and the
 * deactivate or reactivate request, in that order. A field error stops before
 * the status changes; the server checks every rule again.
 */
import { Anchor, Button, Group, Stack, Switch, Text, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import {
  getStore,
  StoreFailed,
  staffStoreKey,
  type StaffStore,
} from "../../../features/stores/adminApi";
import { StoreCard, StoreFormCards } from "../../../features/stores/StoreFormCards";
import {
  HOURS_INVALID,
  hoursErrors,
  markModified,
  modifiedFields,
  toFormValues,
  type StoreFormValues,
} from "../../../features/stores/storeForm";
import classes from "../../../features/stores/stores.module.css";
import { StoreStatusDialog } from "../../../features/stores/StoreStatusDialog";
import {
  serverFieldErrors,
  useStoreSave,
  type StatusChange,
} from "../../../features/stores/useStoreSave";
import {
  allOf,
  hasLength,
  isEmail,
  isPhone,
  isPostalCode,
  isRequired,
} from "../../../shared/forms";
import { EmptyState, ErrorState, LoadingState, Notice, StatusBadge } from "../../../shared/ui";

type Language = "fr" | "en";
const KEY = "storeAdmin.edit";

/** Client checks for formats and required fields; the server has the final word. */
function useStoreForm(store: StaffStore, invalidPostalCode: string) {
  return useForm<StoreFormValues>({
    initialValues: toFormValues(store),
    validate: {
      name: allOf(isRequired(), hasLength({ min: 2, max: 150 })),
      street_number: allOf(isRequired(), hasLength({ max: 10 })),
      street_name: allOf(isRequired(), hasLength({ max: 120 })),
      unit: hasLength({ max: 10 }),
      city: allOf(isRequired(), hasLength({ max: 80 })),
      postal_code: (value) =>
        isRequired()(value) ?? (isPostalCode()(value) ? invalidPostalCode : null),
      phone: allOf(isRequired(), isPhone()),
      email: allOf(isRequired(), isEmail(), hasLength({ max: 254 })),
      pickup_instructions: hasLength({ max: 300 }),
      hours: (value) => (Object.keys(hoursErrors(value)).length ? HOURS_INVALID : null),
    },
  });
}

function StoreSummary({ store }: { store: StaffStore }) {
  const { t, i18n } = useTranslation();
  const since = new Intl.DateTimeFormat(i18n.resolvedLanguage === "en" ? "en-CA" : "fr-CA", {
    month: "long",
    year: "numeric",
  }).format(new Date(store.created_at));
  return (
    <div className={classes.heading}>
      <Text className={classes.eyebrow}>{t(`${KEY}.eyebrow`)}</Text>
      <Title order={1} className={classes.title}>
        {store.name}
      </Title>
      <Text className={classes.subtitle}>
        {store.is_badr
          ? t(`${KEY}.summaryBadr`, { count: store.open_listings })
          : t(`${KEY}.summary`, { since, count: store.open_listings })}
      </Text>
      <Group mt={14}>
        <StatusBadge record="store" status={store.is_active ? "active" : "deactivated"} />
      </Group>
    </div>
  );
}

function StatusCard(props: {
  store: StaffStore;
  active: boolean;
  onChange: (on: boolean) => void;
}) {
  const { store, active, onChange } = props;
  const { t } = useTranslation();
  const key = "storeAdmin.status";
  const help = store.is_badr ? "badrHelp" : active ? "activeHelp" : "inactiveHelp";
  return (
    <StoreCard title={markModified(t(key + ".title"), active !== store.is_active)}>
      <Switch
        checked={active}
        disabled={store.is_badr}
        label={t(`${key}.${active ? "active" : "inactive"}`)}
        description={t(`${key}.${help}`)}
        onChange={(event) => onChange(event.currentTarget.checked)}
      />
    </StoreCard>
  );
}

interface EditNoticesProps {
  store: StaffStore;
  unsaved: boolean;
  errorCount: number;
  pageError: string | null;
}

function EditNotices(props: EditNoticesProps) {
  const { t } = useTranslation();
  return (
    <>
      {props.unsaved && (
        <Notice type="warning" title={t(KEY + ".unsavedTitle")}>
          {t(KEY + ".unsavedBody")}
        </Notice>
      )}
      {!props.store.is_active && (
        <Notice type="info" title={t(`${KEY}.deactivatedAlertTitle`)}>
          {t(`${KEY}.deactivatedAlertBody`)}
        </Notice>
      )}
      {props.errorCount > 0 && (
        <Notice type="error" title={t(`${KEY}.errorsTitle`, { count: props.errorCount })}>
          {t(`${KEY}.errorsBody`)}
        </Notice>
      )}
      {props.pageError && (
        <Notice type="error" title={t(`${KEY}.notSaved`)}>
          {props.pageError}
        </Notice>
      )}
    </>
  );
}

/** Fields that differ from the saved store, and whether anything is unsaved. */
function useUnsaved(store: StaffStore, values: StoreFormValues, statusChange: StatusChange) {
  const initial = useMemo(() => toFormValues(store), [store]);
  const modified = modifiedFields(initial, values);
  return { modified, unsaved: modified.size > 0 || statusChange !== null };
}

/** The form, the status switch, the dialog and the save request of one store. */
function useStoreEditor(store: StaffStore, language: Language) {
  const { t } = useTranslation();
  const form = useStoreForm(store, t(`${KEY}.invalidPostalCode`));
  const [active, setActive] = useState(store.is_active);
  const [dialog, setDialog] = useState<StatusChange>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const statusChange: StatusChange =
    active === store.is_active ? null : active ? "reactivate" : "deactivate";
  const mutation = useStoreSave({
    store,
    form,
    statusChange,
    language,
    onError: (error) => {
      const fields = serverFieldErrors(error);
      if (Object.keys(fields).length) {
        setDialog(null);
        form.setErrors(fields);
      } else if (!dialog) {
        const message = error instanceof StoreFailed ? error.message : t(`${KEY}.networkError`);
        setPageError(message || t(`${KEY}.saveError`));
      }
    },
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    setPageError(null);
    mutation.reset();
    if (form.validate().hasErrors) return;
    if (statusChange) setDialog(statusChange);
    else mutation.mutate(null);
  };
  const closeDialog = () => {
    setDialog(null);
    mutation.reset();
  };
  const { modified, unsaved } = useUnsaved(store, form.values, statusChange);
  return {
    form,
    modified,
    unsaved,
    active,
    setActive,
    dialog,
    closeDialog,
    pageError,
    mutation,
    submit,
  };
}

function StoreEditor({ store, language }: { store: StaffStore; language: Language }) {
  const { t } = useTranslation();
  const editor = useStoreEditor(store, language);
  const { form, active, setActive, dialog, closeDialog, pageError, mutation, submit } = editor;
  return (
    <Stack gap={20}>
      <StoreSummary store={store} />
      <EditNotices
        store={store}
        unsaved={editor.unsaved}
        errorCount={Object.keys(form.errors).length}
        pageError={pageError}
      />
      <form noValidate onSubmit={submit}>
        <Stack gap="lg">
          <StoreFormCards form={form} notes={store.opening_hours.notes} modified={editor.modified}>
            <StatusCard store={store} active={active} onChange={setActive} />
          </StoreFormCards>
          <Group gap="md">
            <Button type="submit" size="md" loading={mutation.isPending && !dialog}>
              {t(`${KEY}.save`)}
            </Button>
            <Anchor component={Link} to="/staff/stores" fw={600}>
              {t(`${KEY}.cancel`)}
            </Anchor>
          </Group>
        </Stack>
      </form>
      {dialog && (
        <StoreStatusDialog
          mode={dialog}
          store={store}
          pending={mutation.isPending}
          error={mutation.error}
          onClose={closeDialog}
          onConfirm={(reason) => mutation.mutate(reason)}
        />
      )}
    </Stack>
  );
}

export function StoreEdit() {
  const { t, i18n } = useTranslation();
  const { id = "" } = useParams();
  const language: Language = i18n.resolvedLanguage === "en" ? "en" : "fr";
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: [...staffStoreKey(id), language],
    queryFn: () => getStore(id, language),
  });
  if (isPending) return <LoadingState />;
  if (isError && error instanceof StoreFailed && error.status === 404) {
    const back = (
      <Button component={Link} to="/staff/stores" variant="default">
        {t(`${KEY}.back`)}
      </Button>
    );
    return <EmptyState title={t(`${KEY}.notFound`)} action={back} />;
  }
  if (isError) return <ErrorState onRetry={() => void refetch()} />;
  return <StoreEditor key={data.id} store={data} language={language} />;
}
