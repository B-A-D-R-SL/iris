// AI contribution: 50% or more AI-generated
// Keep existing translation keys working after splitting files by area.
import enCommon from "./en/common.json";
import enHousehold from "./en/household.json";
import enPublic from "./en/public.json";
import enStaff from "./en/staff.json";
import enStore from "./en/store.json";
import frCommon from "./fr/common.json";
import frHousehold from "./fr/household.json";
import frPublic from "./fr/public.json";
import frStaff from "./fr/staff.json";
import frStore from "./fr/store.json";

export const resources = {
  en: {
    translation: { ...enCommon, ...enHousehold, ...enPublic, ...enStaff, ...enStore },
  },
  fr: {
    translation: { ...frCommon, ...frHousehold, ...frPublic, ...frStaff, ...frStore },
  },
};
