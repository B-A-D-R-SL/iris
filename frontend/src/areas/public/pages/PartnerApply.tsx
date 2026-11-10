// AI contribution: 50% or more AI-generated
import {
  Anchor,
  Button,
  Card,
  Checkbox,
  Chip,
  Group,
  Radio,
  Select,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { getCategories } from "../../../features/categories/api";
import {
  FieldError,
  PhoneField,
  PostalCodeField,
  TextField,
  allOf,
  hasLength,
  isEmail,
  isPhone,
  isPostalCode,
  isRequired,
  validationMessage,
  type Rule,
} from "../../../shared/forms";
import { ErrorState, LoadingState, Notice } from "../../../shared/ui";
import {
  ApplicationError,
  initialValues,
  submitApplication,
  type ApplicationValues,
} from "./partnerApplication";

const types = [
  "grocery",
  "supermarket",
  "bakery",
  "restaurant",
  "cafe",
  "convenience_store",
  "pharmacy",
  "farm_producer",
  "community_organization",
  "other",
] as const;
const frequency = ["daily", "weekly", "monthly", "occasional"] as const;
const namePattern = /^[\p{L}]+(?:[ '’-][\p{L}]+)*$/u;
const slugKey = (s: string) => s.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
const withMessage =
  (rule: Rule<string>, key: string): Rule<string> =>
  (value) =>
    rule(value) ? validationMessage(key) : null;

export function PartnerApply() {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage === "en" ? "en" : "fr";
  const categories = useQuery({ queryKey: ["categories"], queryFn: getCategories });
  const [done, setDone] = useState(false);
  const [tried, setTried] = useState(false);
  const [notice, setNotice] = useState("");
  const noticeRef = useRef<HTMLDivElement>(null);
  const [focusRequest, setFocusRequest] = useState(0);
  useEffect(() => {
    if (focusRequest) noticeRef.current?.focus();
  }, [focusRequest]);
  const showNotice = () => setFocusRequest((x) => x + 1);
  const form = useForm<ApplicationValues>({
    initialValues,
    validate: {
      business_name: withMessage(
        allOf(isRequired(), hasLength({ min: 2, max: 150 })),
        "store.partnerForm.invalidBusinessName",
      ),
      business_type: (v) =>
        types.includes(v as (typeof types)[number]) ? null : t("shared.validation.required"),
      neq: (v) => (!v || /^\d{10}$/.test(v) ? null : t("store.partnerForm.invalidNeq")),
      website: (v) => {
        if (!v.trim()) return null;
        try {
          const u = new URL(/^https?:\/\//i.test(v) ? v : `https://${v}`);
          return ["http:", "https:"].includes(u.protocol) && u.hostname.includes(".")
            ? null
            : t("store.partnerForm.invalidWebsite");
        } catch {
          return t("store.partnerForm.invalidWebsite");
        }
      },
      street_number: (v) =>
        /^\d{1,8}(?:[A-Za-z]| ?\d\/\d)?$/.test(v.trim())
          ? null
          : t("store.partnerForm.invalidStreetNumber"),
      street_name: allOf(isRequired(), hasLength({ min: 2, max: 120 })),
      city: allOf(isRequired(), hasLength({ max: 80 })),
      postal_code: withMessage(
        allOf(isRequired(), isPostalCode()),
        "store.partnerForm.invalidPostalCode",
      ),
      contact_first_name: (v) =>
        v.trim().length <= 100 && namePattern.test(v.trim())
          ? null
          : t("store.partnerForm.invalidName"),
      contact_last_name: (v) =>
        v.trim().length <= 100 && namePattern.test(v.trim())
          ? null
          : t("store.partnerForm.invalidName"),
      contact_email: withMessage(
        allOf(isRequired(), isEmail(), hasLength({ max: 254 })),
        "store.partnerForm.invalidEmail",
      ),
      contact_phone: allOf(isRequired(), isPhone()),
      goods_categories: (v) => (v.length ? null : t("store.partnerForm.chooseGoods")),
      expected_frequency: (v) =>
        frequency.includes(v as (typeof frequency)[number])
          ? null
          : t("shared.validation.required"),
      opening_hours: allOf(isRequired(), hasLength({ max: 300 })),
      consent_contact: (v) => (v ? null : t("store.partnerForm.requireConsent")),
    },
  });
  const mutation = useMutation({
    mutationFn: (values: ApplicationValues) => submitApplication(values, language),
    onSuccess: () => {
      setDone(true);
      window.scrollTo(0, 0);
    },
    onError: (error) => {
      if (
        error instanceof ApplicationError &&
        error.status === 400 &&
        Object.keys(error.fields).length
      ) {
        const errors: Record<string, string> = {};
        for (const [key, value] of Object.entries(error.fields))
          if (Array.isArray(value) && typeof value[0] === "string") errors[key] = value[0];
        form.setErrors(errors);
        setTried(true);
        setNotice("");
      } else {
        setNotice(
          error instanceof ApplicationError && error.message
            ? error.message
            : t("store.partnerForm.failure"),
        );
      }
      showNotice();
    },
  });
  if (done)
    return (
      <Stack gap="md">
        <Title order={1}>{t("store.partnerForm.successTitle")}</Title>
        <Text>{t("store.partnerForm.successMessage", { email: form.values.contact_email })}</Text>
        <Card withBorder>
          <Stack gap="xs">
            <Title order={2} size="h4">
              {t("store.partnerForm.nextTitle")}
            </Title>
            <Text>{t("store.partnerForm.nextMessage")}</Text>
          </Stack>
        </Card>
        <Button component={Link} to="/" variant="outline">
          {t("store.partnerForm.home")}
        </Button>
      </Stack>
    );
  const count = Object.values(form.errors).filter(Boolean).length;
  const optional = true;
  return (
    <Stack gap="md">
      <Title order={1}>{t("store.partnerApplication.becomePartner")}</Title>
      <Text c="dimmed">{t("store.partnerForm.description")}</Text>
      <div ref={noticeRef} tabIndex={-1}>
        {notice ? (
          <Notice type="error" title={t("store.partnerForm.submitError")}>
            {notice}
          </Notice>
        ) : tried && count > 0 ? (
          <Notice type="error" title={t("store.partnerForm.errorSummary", { total: count })}>
            {t("store.partnerForm.errorsKept")}
          </Notice>
        ) : null}
      </div>
      <Text size="sm" c="dimmed">
        {t("shared.form.requiredNotice")}
      </Text>
      <form
        noValidate
        onSubmit={form.onSubmit(
          (values) => {
            setNotice("");
            setTried(false);
            mutation.mutate(values);
          },
          () => {
            setNotice("");
            setTried(true);
            showNotice();
          },
        )}
      >
        <Stack gap="md">
          <Title order={2} size="h4">
            {t("store.partnerForm.businessSection")}
          </Title>
          <TextField
            label={t("store.partnerApplication.businessName")}
            maxLength={150}
            {...form.getInputProps("business_name")}
          />
          <Select
            label={t("store.partnerApplication.businessType")}
            aria-required="true"
            data={types.map((v) => ({
              value: v,
              label: t(`store.partnerApplication.businessTypes.${slugKey(v)}`),
            }))}
            {...form.getInputProps("business_type")}
          />
          <TextField
            label={t("store.partnerApplication.neq")}
            optional={optional}
            maxLength={10}
            {...form.getInputProps("neq")}
          />
          <TextField
            label={t("store.partnerApplication.website")}
            optional={optional}
            maxLength={200}
            {...form.getInputProps("website")}
          />
          <Title order={2} size="h4">
            {t("store.partnerForm.addressSection")}
          </Title>
          <Group grow align="start">
            <TextField
              label={t("household.registrationAddress.streetNumber")}
              maxLength={10}
              {...form.getInputProps("street_number")}
            />
            <TextField
              label={t("household.registrationAddress.streetName")}
              maxLength={120}
              {...form.getInputProps("street_name")}
            />
          </Group>
          <Group grow align="start">
            <TextField
              label={t("household.registrationAddress.unit")}
              optional={optional}
              maxLength={10}
              {...form.getInputProps("unit")}
            />
            <TextField
              label={t("household.registrationAddress.city")}
              maxLength={80}
              {...form.getInputProps("city")}
            />
          </Group>
          <PostalCodeField
            label={t("household.registrationAddress.postalCode")}
            {...form.getInputProps("postal_code")}
          />
          <Title order={2} size="h4">
            {t("store.partnerForm.contactSection")}
          </Title>
          <Group grow align="start">
            <TextField
              label={t("store.partnerApplication.contactFirstName")}
              maxLength={100}
              {...form.getInputProps("contact_first_name")}
            />
            <TextField
              label={t("store.partnerApplication.contactLastName")}
              maxLength={100}
              {...form.getInputProps("contact_last_name")}
            />
          </Group>
          <TextField
            label={t("store.partnerApplication.contactRole")}
            optional={optional}
            maxLength={100}
            {...form.getInputProps("contact_role")}
          />
          <TextField
            label={t("store.partnerApplication.contactEmail")}
            type="email"
            maxLength={254}
            description={t("store.partnerForm.emailHelp")}
            {...form.getInputProps("contact_email")}
          />
          <PhoneField
            label={t("store.partnerApplication.contactPhone")}
            {...form.getInputProps("contact_phone")}
          />
          <Title order={2} size="h4">
            {t("store.partnerForm.donationsSection")}
          </Title>
          <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
            <legend>{t("store.partnerApplication.goodsCategories")}</legend>
            <Text size="sm" c="dimmed">
              {t("store.partnerForm.chooseGoods")}
            </Text>
            {form.errors.goods_categories && (
              <Text size="sm" role="alert">
                <FieldError>{form.errors.goods_categories}</FieldError>
              </Text>
            )}
            {categories.isPending ? (
              <LoadingState />
            ) : categories.isError ? (
              <ErrorState onRetry={() => void categories.refetch()} />
            ) : categories.data.length === 0 ? (
              <Notice type="warning">{t("store.partnerForm.noCategories")}</Notice>
            ) : (
              <Chip.Group
                multiple
                value={form.values.goods_categories}
                onChange={(v) => form.setFieldValue("goods_categories", v)}
              >
                <Group gap="xs" mt="xs">
                  {categories.data.map((item) => (
                    <Chip key={item.code} value={item.code}>
                      {language === "en" ? item.name_en : item.name_fr}
                    </Chip>
                  ))}
                </Group>
              </Chip.Group>
            )}
          </fieldset>
          <Radio.Group
            label={t("store.partnerApplication.expectedFrequency")}
            value={form.values.expected_frequency}
            onChange={(v) => form.setFieldValue("expected_frequency", v)}
            error={form.errors.expected_frequency}
            withAsterisk
          >
            <Group mt="xs">
              {frequency.map((v) => (
                <Radio
                  key={v}
                  value={v}
                  label={t(`store.partnerApplication.donationFrequency.${v}`)}
                />
              ))}
            </Group>
          </Radio.Group>
          <TextField
            label={t("store.partnerApplication.openingHours")}
            multiline
            maxLength={300}
            {...form.getInputProps("opening_hours")}
          />
          <TextField
            label={t("store.partnerApplication.message")}
            multiline
            optional={optional}
            maxLength={1000}
            {...form.getInputProps("message")}
          />
          <Checkbox
            label={t("store.partnerApplication.consentContact")}
            {...form.getInputProps("consent_contact", { type: "checkbox" })}
          />
          <Text size="sm" c="dimmed">
            {t("store.partnerForm.privacyHelp")}{" "}
            <Anchor component={Link} to="/privacy">
              {t("privacy.common.privacyPolicy")}
            </Anchor>
          </Text>
          <Button
            type="submit"
            fullWidth
            loading={mutation.isPending}
            disabled={categories.isPending || categories.isError || !categories.data?.length}
          >
            {t("store.partnerForm.send")}
          </Button>
        </Stack>
      </form>
    </Stack>
  );
}
