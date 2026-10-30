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
  maxMb: number;
  /** Text in the drop zone, for example "Prendre ou choisir une photo". */
  buttonLabel?: string;
  icon?: TablerIcon;
}

/** One private file (photo or notice). Phones offer the camera for image types. */
export function FileUpload(props: FileUploadProps) {
  const { value = null, onChange, accept, maxMb, icon: ZoneIcon = IconCamera } = props;
  const { t } = useTranslation();
  const wrapper = useFieldWrapper(props);
  const generatedId = useId();
  const id = props.id ?? generatedId;
  const types = fileTypeNames(accept);
  // The buttons are not Mantine inputs, so link them to the helper and error text ourselves.
  const descriptionId = `${id}-description`;
  const errorId = `${id}-error`;
  const hasError = Boolean(wrapper.error) && typeof wrapper.error !== "boolean";
  const describedBy =
    [hasError ? errorId : null, wrapper.description ? descriptionId : null]
      .filter(Boolean)
      .join(" ") || undefined;

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
      {value ? (
        <div className={classes.fileRow}>
          <IconFile size={24} stroke={2} aria-hidden />
          <Stack gap={0} style={{ flex: 1, minWidth: 0 }}>
            <Text size="sm" fw={600} truncate>
              {value.name}
            </Text>
            <Text size="xs" c="gray.7">
              {t("shared.fileUpload.size", { size: value.size / (1024 * 1024) })}
            </Text>
          </Stack>
          <FileButton onChange={onChange} accept={accept.join(",")}>
            {(buttonProps) => (
              <Button
                {...buttonProps}
                id={id}
                aria-describedby={describedBy}
                variant="subtle"
                size="sm"
                disabled={props.disabled}
              >
                {t("shared.fileUpload.change")}
              </Button>
            )}
          </FileButton>
          <Button
            variant="subtle"
            size="sm"
            onClick={() => onChange(null)}
            disabled={props.disabled}
          >
            {t("shared.fileUpload.remove")}
          </Button>
        </div>
      ) : (
        <FileButton onChange={onChange} accept={accept.join(",")}>
          {(buttonProps) => (
            <UnstyledButton
              {...buttonProps}
              id={id}
              name={props.name}
              className={classes.dropZone}
              data-error={props.error ? true : undefined}
              aria-required={wrapper["aria-required"]}
              aria-describedby={describedBy}
              disabled={props.disabled}
              onBlur={props.onBlur}
              onFocus={props.onFocus}
            >
              <ZoneIcon size={24} stroke={2} aria-hidden />
              <Text size="sm" fw={600}>
                {props.buttonLabel ?? t("shared.fileUpload.choose")}
              </Text>
              <Text size="xs" c="gray.7">
                {t("shared.fileUpload.limits", { types, max: maxMb })}
              </Text>
            </UnstyledButton>
          )}
        </FileButton>
      )}
    </Input.Wrapper>
  );
}
