// AI contribution: 50% or more AI-generated
import { Button, FileButton, Input, Stack, Text, UnstyledButton } from "@mantine/core";
import { IconCamera, IconFile, type TablerIcon } from "@tabler/icons-react";
import { useId } from "react";
import { useTranslation } from "react-i18next";

import { useFieldWrapper, type BaseFieldProps } from "./fieldProps";
import classes from "./fields.module.css";
import { fileTypeNames } from "./validators";

export interface FileUploadProps extends BaseFieldProps {
  value?: File | null;
  onChange: (file: File | null) => void;
  /** MIME types, for example ["image/jpeg", "image/png"]. Check them with isAcceptedFile too. */
  accept: readonly string[];
  maxMb?: number;
  /** Text in the drop zone, for example "Prendre ou choisir une photo". */
  buttonLabel?: string;
  icon?: TablerIcon;
}

/** What the file buttons share: they are not Mantine inputs, so they carry their own links. */
interface FileButtonWiring {
  id: string;
  describedBy?: string;
  accept: readonly string[];
  onChange: (file: File | null) => void;
  disabled?: boolean;
}

/** The chosen file, with "Changer" and "Retirer". */
function ChosenFile({ file, wiring }: { file: File; wiring: FileButtonWiring }) {
  const { t } = useTranslation();
  return (
    <div className={classes.fileRow}>
      <IconFile size={24} stroke={2} aria-hidden />
      <Stack gap={0} style={{ flex: 1, minWidth: 0 }}>
        <Text size="sm" fw={600} truncate>
          {file.name}
        </Text>
        <Text size="xs" c="dimmed">
          {t("shared.fileUpload.size", { size: file.size / (1024 * 1024) })}
        </Text>
      </Stack>
      <FileButton onChange={wiring.onChange} accept={wiring.accept.join(",")}>
        {(buttonProps) => (
          <Button
            {...buttonProps}
            id={wiring.id}
            aria-describedby={wiring.describedBy}
            variant="subtle"
            size="sm"
            disabled={wiring.disabled}
          >
            {t("shared.fileUpload.change")}
          </Button>
        )}
      </FileButton>
      <Button
        variant="subtle"
        size="sm"
        onClick={() => wiring.onChange(null)}
        disabled={wiring.disabled}
      >
        {t("shared.fileUpload.remove")}
      </Button>
    </div>
  );
}

/** The empty drop zone: the button, with the accepted types and size. */
function DropZone({ props, wiring }: { props: FileUploadProps; wiring: FileButtonWiring }) {
  const { t } = useTranslation();
  const { icon: ZoneIcon = IconCamera, maxMb } = props;
  const types = fileTypeNames(wiring.accept);
  return (
    <FileButton onChange={wiring.onChange} accept={wiring.accept.join(",")}>
      {(buttonProps) => (
        <UnstyledButton
          {...buttonProps}
          id={wiring.id}
          name={props.name}
          className={classes.dropZone}
          data-error={props.error ? true : undefined}
          aria-required={props.optional ? undefined : true}
          aria-describedby={wiring.describedBy}
          disabled={wiring.disabled}
          onBlur={props.onBlur}
          onFocus={props.onFocus}
        >
          <ZoneIcon size={24} stroke={2} aria-hidden />
          <Text size="sm" fw={600}>
            {props.buttonLabel ?? t("shared.fileUpload.choose")}
          </Text>
          <Text size="xs" c="dimmed">
            {maxMb === undefined ? types : t("shared.fileUpload.limits", { types, max: maxMb })}
          </Text>
        </UnstyledButton>
      )}
    </FileButton>
  );
}

/** One private file (photo or notice). Phones offer the camera for image types. */
export function FileUpload(props: FileUploadProps) {
  const wrapper = useFieldWrapper(props);
  const generatedId = useId();
  const id = props.id ?? generatedId;
  const descriptionId = `${id}-description`;
  const errorId = `${id}-error`;
  const hasError = Boolean(wrapper.error) && typeof wrapper.error !== "boolean";
  const describedBy =
    [hasError ? errorId : null, wrapper.description ? descriptionId : null]
      .filter(Boolean)
      .join(" ") || undefined;
  const wiring = {
    id,
    describedBy,
    accept: props.accept,
    onChange: props.onChange,
    disabled: props.disabled,
  };

  return (
    <Input.Wrapper
      label={wrapper.label}
      description={wrapper.description}
      error={wrapper.error}
      withAsterisk={false}
      inputWrapperOrder={wrapper.inputWrapperOrder}
      id={id}
      descriptionProps={{ id: descriptionId }}
      errorProps={{ id: errorId }}
    >
      {props.value ? (
        <ChosenFile file={props.value} wiring={wiring} />
      ) : (
        <DropZone props={props} wiring={wiring} />
      )}
    </Input.Wrapper>
  );
}
