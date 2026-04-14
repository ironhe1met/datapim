import { z } from 'zod';

const envSchema = z.object({
  VITE_API_URL: z.string().default('http://localhost:8000'),
  VITE_APP_NAME: z.string().default('DataPIM'),
  VITE_MSW_ENABLED: z.string().optional(),
});

export const env = envSchema.parse({
  VITE_API_URL: import.meta.env.VITE_API_URL,
  VITE_APP_NAME: import.meta.env.VITE_APP_NAME,
  VITE_MSW_ENABLED: import.meta.env.VITE_MSW_ENABLED,
});
