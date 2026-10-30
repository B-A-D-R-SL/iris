// AI contribution: 50% or more AI-generated
/**
 * Iris design tokens, taken from the Figma Components page (SET-11).
 * The wireframes are grayscale on purpose: meaning is carried by icons,
 * borders and text, never colour alone.
 */
import {
  Alert,
  AppShell,
  Badge,
  Button,
  createTheme,
  Input,
  InputWrapper,
  Loader,
  rem,
  type CSSVariablesResolver,
} from "@mantine/core";

import { INPUT_WRAPPER_ORDER } from "../shared/forms/fieldProps";
import classes from "./theme.module.css";

export const theme = createTheme({
  primaryColor: "gray",
  primaryShade: 9,
  black: "#212529",
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
      vars: (_theme, props) =>
        (props.size ?? "md") === "md"
          ? {
              root: {
                "--button-height": rem(48),
                "--button-padding-x": rem(20),
                "--button-fz": rem(16),
              },
            }
          : { root: {} },
    }),
    // 44 px inputs with 16 px text, so iOS does not zoom (Figma "Field").
    Input: Input.extend({
      defaultProps: { size: "md" },
      classNames: { input: classes.input },
      vars: (_theme, props) =>
        (props.size ?? "md") === "md"
          ? { wrapper: { "--input-height": rem(44), "--input-fz": rem(16) } }
          : { wrapper: {} },
    }),
    InputWrapper: InputWrapper.extend({
      defaultProps: { size: "md", inputWrapperOrder: INPUT_WRAPPER_ORDER },
      classNames: { label: classes.label, description: classes.description, error: classes.error },
    }),
    // Grayscale alerts; shared/ui/Notice adds the icon per type (Figma "Alert").
    Alert: Alert.extend({
      defaultProps: { variant: "default", radius: "md" },
      classNames: { title: classes.alertTitle },
    }),
    Badge: Badge.extend({ defaultProps: { radius: "xl" } }),
    Loader: Loader.extend({ defaultProps: { type: "dots" } }),
    AppShell: AppShell.extend({ defaultProps: { padding: 0 } }),
  },
});

/** Grayscale error colour, and a placeholder colour that meets WCAG 4.5:1 (NFR-03). */
export const cssVariablesResolver: CSSVariablesResolver = () => ({
  variables: {},
  light: {
    "--mantine-color-error": "var(--mantine-color-gray-9)",
    "--mantine-color-placeholder": "#6c757d",
  },
  dark: {},
});
