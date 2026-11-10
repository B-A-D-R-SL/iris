// AI contribution: 50% or more AI-generated
import {
  Alert,
  AppShell,
  Badge,
  Button,
  Card,
  Checkbox,
  Chip,
  Radio,
  Table,
  SegmentedControl,
  Modal,
  Drawer,
  Paper,
  defaultVariantColorsResolver,
  createTheme,
  Input,
  InputWrapper,
  Loader,
  rem,
  type CSSVariablesResolver,
} from "@mantine/core";

import { INPUT_WRAPPER_ORDER } from "../shared/forms/fieldProps";
import classes from "./theme.module.css";
import { palettes, primaryShade, tokens, tokenVariables } from "./tokens";

const toneTokens = {
  iris: ["primary", "primary-light"],
  success: ["success-strong", "success-light"],
  warning: ["warning-strong", "warning-light"],
  danger: ["danger-strong", "danger-light"],
  info: ["info-strong", "info-light"],
  neutral: ["neutral-strong", "neutral-light"],
} as const;

/** Narrow semantic aliases while preserving Mantine's handling of explicit shade names. */
function isToneColor(color: string): color is keyof typeof toneTokens {
  return Object.hasOwn(toneTokens, color);
}

export const theme = createTheme({
  colors: palettes,
  primaryColor: "iris",
  primaryShade,
  /** Resolve semantic foreground/background pairs for filled, light and outline variants. */
  variantColorResolver: (input) => {
    const color = input.color ?? input.theme.primaryColor;
    const fallback = defaultVariantColorsResolver({ ...input, color });
    if (!isToneColor(color)) return fallback;
    const [strong, light] = toneTokens[color];
    if (input.variant === "filled")
      return {
        ...fallback,
        background: `var(--iris-${strong})`,
        color: "var(--iris-on-primary)",
        hover: color === "iris" ? "var(--iris-primary-hover)" : `var(--iris-${strong})`,
      };
    if (input.variant === "light")
      return {
        ...fallback,
        background: `var(--iris-${light})`,
        color: `var(--iris-${strong})`,
        hover: `var(--iris-${light})`,
      };
    if (input.variant === "outline")
      return {
        ...fallback,
        border: `1px solid var(--iris-${strong})`,
        color: `var(--iris-${strong})`,
        hover: `var(--iris-${light})`,
      };
    return fallback;
  },
  black: tokens.text,
  white: tokens.onPrimary,
  focusClassName: classes.focus,
  fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  defaultRadius: "sm",
  radius: { xs: rem(2), sm: rem(4), md: rem(6), lg: rem(8), xl: rem(14) },
  // WF/Caption 12/16, WF/Body 14/20, WF/Input 16/24, WF/Heading 18/24, WF/Title 22/28
  fontSizes: { xs: rem(12), sm: rem(14), md: rem(16), lg: rem(18), xl: rem(22) },
  lineHeights: { xs: "1.333", sm: "1.43", md: "1.5", lg: "1.333", xl: "1.27" },
  headings: {
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    fontWeight: "600",
    sizes: {
      h1: { fontSize: rem(22), lineHeight: "1.27", fontWeight: "700" },
      h2: { fontSize: rem(18), lineHeight: "1.333" },
      h3: { fontSize: rem(16), lineHeight: "1.5" },
      h4: { fontSize: rem(14), lineHeight: "1.43" },
    },
  },
  components: {
    // "md" is the default size, tuned to the Figma values; pass size="sm" for compact controls.
    // 48 px buttons: touch target for gloves (Figma "Button").
    Button: Button.extend({
      defaultProps: { size: "md" },
      classNames: { root: classes.button },
      /** Retain compact sizes and add the published primary pressed state. */
      vars: (_theme, props) => ({
        root: {
          ...((props.size ?? "md") === "md"
            ? {
                "--button-height": rem(48),
                "--button-padding-x": rem(20),
                "--button-fz": rem(16),
              }
            : {}),
          "--button-pressed":
            !props.color || props.color === "iris" ? "var(--iris-primary-pressed)" : undefined,
        },
      }),
    }),
    // 44 px inputs with 16 px text, so iOS does not zoom (Figma "Field").
    Input: Input.extend({
      defaultProps: { size: "md" },
      classNames: { input: classes.input },
      /** Apply touch-friendly dimensions only to the standard input size. */
      vars: (_theme, props) =>
        (props.size ?? "md") === "md"
          ? { wrapper: { "--input-height": rem(44), "--input-fz": rem(16) } }
          : { wrapper: {} },
    }),
    InputWrapper: InputWrapper.extend({
      defaultProps: { size: "md", inputWrapperOrder: INPUT_WRAPPER_ORDER },
      classNames: { label: classes.label, description: classes.description, error: classes.error },
    }),
    // Shared Notice adds the icon and semantic colours per type.
    Alert: Alert.extend({
      defaultProps: { variant: "default", radius: "md" },
      classNames: { title: classes.alertTitle },
    }),
    SegmentedControl: SegmentedControl.extend({ classNames: { label: classes.segmentLabel } }),
    Modal: Modal.extend({
      styles: {
        content: { backgroundColor: "var(--iris-surface)" },
        header: { backgroundColor: "var(--iris-surface)" },
      },
    }),
    Drawer: Drawer.extend({
      styles: {
        content: { backgroundColor: "var(--iris-surface)" },
        header: { backgroundColor: "var(--iris-surface)" },
      },
    }),
    Checkbox: Checkbox.extend({ classNames: { input: classes.checkControl } }),
    Radio: Radio.extend({ classNames: { radio: classes.checkControl } }),
    Chip: Chip.extend({ classNames: { label: classes.choiceLabel } }),
    Table: Table.extend({
      vars: () => ({
        table: {
          "--table-border-color": "var(--iris-border)",
          "--table-striped-color": "var(--iris-surface-raised)",
          "--table-highlight-on-hover-color": "var(--iris-neutral-light)",
        },
      }),
    }),
    Card: Card.extend({ styles: { root: { backgroundColor: "var(--iris-surface-raised)" } } }),
    Paper: Paper.extend({ styles: { root: { backgroundColor: "var(--iris-surface-raised)" } } }),
    Badge: Badge.extend({ defaultProps: { radius: "xl" } }),
    Loader: Loader.extend({ defaultProps: { type: "dots" } }),
    AppShell: AppShell.extend({ defaultProps: { padding: 0 } }),
  },
});

/** Semantic aliases keep Mantine defaults and shared components on the same tokens. */
export const cssVariablesResolver: CSSVariablesResolver = () => ({
  variables: tokenVariables,
  light: {
    "--mantine-color-text": "var(--iris-text)",
    "--mantine-color-body": "var(--iris-surface)",
    "--mantine-color-dimmed": "var(--iris-text-muted)",
    "--mantine-color-placeholder": "var(--iris-text-placeholder)",
    "--mantine-color-error": "var(--iris-danger-strong)",
    "--mantine-color-default-border": "var(--iris-border)",
    "--mantine-color-iris-filled": "var(--iris-primary)",
    "--mantine-color-iris-filled-hover": "var(--iris-primary-hover)",
    "--mantine-color-default": "var(--iris-surface-raised)",
  },
  dark: {},
});
