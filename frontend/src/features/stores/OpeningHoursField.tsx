// AI contribution: 50% or more AI-generated
/**
 * The weekly opening-hours grid of the store edit screen (Figma W7.2): one
 * opening and closing time per day, or "Closed".
 */
import { Checkbox, Group, Stack, Text, TextInput } from "@mantine/core";
import { useTranslation } from "react-i18next";

import { FieldError } from "../../shared/forms";
import {
  completeTime,
  DAYS,
  formatTime,
  type Day,
  type DayValue,
  type HoursError,
} from "./storeForm";

const KEY = "storeAdmin.hours";

export interface OpeningHoursFieldProps {
  value: Record<Day, DayValue>;
  onChange: (day: Day, value: DayValue) => void;
  errors: Partial<Record<Day, HoursError>> & { week?: "noOpenDay" };
  /** Free text copied from the partner application, shown until replaced. */
  notes?: string | null;
  /** Changed but not saved (`hours.mon`...): the day name gets a "*". */
  modified?: Set<string>;
}

interface DayRowProps {
  day: Day;
  value: DayValue;
  error?: HoursError;
  modified: boolean;
  onChange: (value: DayValue) => void;
}

function DayRow({ day, value, error, modified, onChange }: DayRowProps) {
  const { t } = useTranslation();
  const dayName = t(`${KEY}.${day}`);
  const update = (changes: Partial<DayValue>) => onChange({ ...value, ...changes });
  // A plain 24-hour text box: the browser's time picker shows "--:--" and,
  // with a 12-hour locale, misreads typed times such as 20:00.
  const time = (field: "open" | "close", label: string) => (
    <TextInput
      aria-label={t(`${KEY}.${label}`, { day: dayName })}
      value={value[field]}
      placeholder={value.closed ? "" : "08:00"}
      inputMode="numeric"
      maxLength={5}
      autoComplete="off"
      disabled={value.closed}
      error={Boolean(error)}
      onChange={(event) => update({ [field]: formatTime(event.currentTarget.value) })}
      onBlur={() => update({ [field]: completeTime(value[field]) })}
      w={80}
    />
  );
  return (
    <div>
      <Group gap="xs" wrap="nowrap" align="center">
        <Text fw={600} w={44} aria-hidden>
          {modified ? dayName + " *" : dayName}
        </Text>
        {time("open", "opens")}
        <Text size="sm" aria-hidden>
          {t(`${KEY}.to`)}
        </Text>
        {time("close", "closes")}
        <Checkbox
          label={t(`${KEY}.closed`)}
          aria-label={t(`${KEY}.closedDay`, { day: dayName })}
          checked={value.closed}
          onChange={(event) =>
            update(
              event.currentTarget.checked
                ? { closed: true, open: "", close: "" }
                : { closed: false },
            )
          }
        />
      </Group>
      {error && <FieldError>{t(`${KEY}.${error}`)}</FieldError>}
    </div>
  );
}

export function OpeningHoursField(props: OpeningHoursFieldProps) {
  const { value, onChange, errors, notes, modified } = props;
  const { t } = useTranslation();
  return (
    <Stack gap="xs">
      {notes && (
        <Text size="sm" c="dimmed">
          {t(`${KEY}.notes`, { notes })}
        </Text>
      )}
      {DAYS.map((day) => (
        <DayRow
          key={day}
          day={day}
          value={value[day]}
          error={errors[day]}
          modified={modified?.has("hours." + day) ?? false}
          onChange={(dayValue) => onChange(day, dayValue)}
        />
      ))}
      {errors.week && <FieldError>{t(`${KEY}.${errors.week}`)}</FieldError>}
    </Stack>
  );
}
