// AI contribution: 50% or more AI-generated
// Date pickers (@mantine/dates) use dayjs: load French and the parser for typed dates.
import dayjs from "dayjs";
import customParseFormat from "dayjs/plugin/customParseFormat";
import "dayjs/locale/fr";

dayjs.extend(customParseFormat);
