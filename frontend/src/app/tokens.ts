// AI contribution: 50% or more AI-generated
import type { MantineColorsTuple } from "@mantine/core";

/** SET-33 Foundations.png, merged by PR #668: ten shades copied value for value. */
export const foundationsPalettes = {
  irisGreen: [
    "#EFFAF0",
    "#DEF3E0",
    "#B8E7BC",
    "#8FDB96",
    "#6DD075",
    "#58CA60",
    "#4DC755",
    "#3EAF46",
    "#349C3D",
    "#237A2C",
  ],
  irisNavy: [
    "#EBF8FF",
    "#D6EEFA",
    "#A8DDF7",
    "#79CBF5",
    "#59BBF3",
    "#48B2F2",
    "#3EADF3",
    "#3297D9",
    "#2587C2",
    "#013751",
  ],
  irisSand: [
    "#FEF3EA",
    "#EEE6E0",
    "#D4CCC6",
    "#BAB1AA",
    "#A39991",
    "#968A81",
    "#908378",
    "#7D7065",
    "#716358",
    "#655447",
  ],
  irisSlate: [
    "#F3F5F7",
    "#E7E7E7",
    "#CACED0",
    "#ABB3B9",
    "#909CA5",
    "#7E8E9A",
    "#748795",
    "#627482",
    "#556775",
    "#455968",
  ],
  irisOrange: [
    "#FFF4E2",
    "#FFE8CD",
    "#FDCF9D",
    "#FBB568",
    "#FA9F3C",
    "#F99120",
    "#F98A0F",
    "#DE7702",
    "#C66900",
    "#AD5900",
  ],
  irisRed: [
    "#FFECE7",
    "#FFD8D1",
    "#F9AFA2",
    "#F48470",
    "#EF5F45",
    "#ED482A",
    "#ED3B1B",
    "#D32D0F",
    "#BD250B",
    "#A51A05",
  ],
  irisBlue: [
    "#E5F9FF",
    "#D0EEFF",
    "#9FDBFD",
    "#6DC7FB",
    "#48B7FA",
    "#34ACFA",
    "#28A7FB",
    "#1992E0",
    "#0082C9",
    "#0070B2",
  ],
} satisfies Record<string, MantineColorsTuple>;

/** Stable application palette names let screens keep using the SET-34 interface. */
export const palettes = {
  ...foundationsPalettes,
  // Mantine internal neutral defaults use the same warm Foundations scale.
  gray: foundationsPalettes.irisSand,
  iris: foundationsPalettes.irisGreen,
  success: foundationsPalettes.irisGreen,
  warning: foundationsPalettes.irisOrange,
  danger: foundationsPalettes.irisRed,
  info: foundationsPalettes.irisBlue,
  neutral: foundationsPalettes.irisSand,
};
export const primaryShade = 9;
export const referenceColors = { black: "#000000", white: "#FFFFFF" };

/** Semantic and component tokens from the Foundations table and its component-token note. */
export const tokens = {
  primary: palettes.iris[primaryShade],
  primaryHover: "#1D6824",
  primaryPressed: "#17561D",
  onPrimary: referenceColors.white,
  text: foundationsPalettes.irisNavy[9],
  textMuted: foundationsPalettes.irisSlate[9],
  textPlaceholder: foundationsPalettes.irisSlate[7],
  surface: referenceColors.white,
  surfaceRaised: foundationsPalettes.irisSand[0],
  // Foundations distinguishes decorative borders from control boundaries.
  border: foundationsPalettes.irisSand[1],
  inputBorder: foundationsPalettes.irisSand[5],
  neutralStrong: foundationsPalettes.irisNavy[9],
  neutralLight: foundationsPalettes.irisSand[1],
  primaryLight: palettes.iris[1],
  successStrong: palettes.success[9],
  successLight: palettes.success[1],
  warningStrong: palettes.warning[9],
  warningLight: palettes.warning[0],
  warningBorder: palettes.warning[6],
  dangerStrong: palettes.danger[8],
  dangerLight: palettes.danger[0],
  infoStrong: palettes.info[9],
  infoLight: palettes.info[0],
} as const;

/** camelCase token names become public CSS names, e.g. inputBorder -> input-border. */
export const tokenVariables = Object.fromEntries(
  Object.entries(tokens).map(([name, value]) => [
    `--iris-${name.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)}`,
    value,
  ]),
);
