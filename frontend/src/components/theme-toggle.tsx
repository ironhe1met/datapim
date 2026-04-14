import { Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useThemeStore } from '@/stores/theme-store';

export function ThemeToggle() {
  const { theme, toggle } = useThemeStore();

  return (
    <Button variant="ghost" size="icon" onClick={toggle}>
      {theme === 'light' ? (
        <Moon className="h-5 w-5" />
      ) : (
        <Sun className="h-5 w-5" />
      )}
      <span className="sr-only">
        {theme === 'light' ? 'Dark mode' : 'Light mode'}
      </span>
    </Button>
  );
}
