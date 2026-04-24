import { SunIcon, MoonIcon, MonitorIcon } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/lib/theme";
import type { Theme } from "@/lib/theme";

const NEXT_THEME: Record<Theme, Theme> = {
  auto: "light",
  light: "dark",
  dark: "auto",
};

const LABEL: Record<Theme, string> = {
  auto: "Auto (system)",
  light: "Light",
  dark: "Dark",
};

/** Three-state cycle button: auto → light → dark → auto. */
export function ThemeToggle() {
  const [theme, setTheme] = useTheme();
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(NEXT_THEME[theme])}
      aria-label={`Theme: ${LABEL[theme]}. Click to switch.`}
      title={LABEL[theme]}
    >
      {theme === "light" ? (
        <SunIcon size={15} />
      ) : theme === "dark" ? (
        <MoonIcon size={15} />
      ) : (
        <MonitorIcon size={15} />
      )}
    </Button>
  );
}
