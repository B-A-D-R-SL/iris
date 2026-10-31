// AI contribution: 50% or more AI-generated
import { Group, Text } from "@mantine/core";

/** "Iris" + a small subtitle, as in the Figma public app bar and staff top bar. */
export function Wordmark({ subtitle, strong = false }: { subtitle: string; strong?: boolean }) {
  return (
    <Group gap={8} align="baseline" wrap="nowrap" miw={0}>
      <Text component="span" fz="xl" fw={700} lh="xl" style={{ flexShrink: 0 }}>
        Iris
      </Text>
      <Text component="span" fz="xs" fw={strong ? 600 : 400} c="gray.7" truncate>
        {subtitle}
      </Text>
    </Group>
  );
}
