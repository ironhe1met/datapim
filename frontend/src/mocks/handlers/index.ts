import { authHandlers } from '@/mocks/handlers/auth';
import { dashboardHandlers } from '@/mocks/handlers/dashboard';
import { productHandlers } from '@/mocks/handlers/products';
import { categoryHandlers } from '@/mocks/handlers/categories';
import { reviewHandlers } from '@/mocks/handlers/reviews';
import { userHandlers } from '@/mocks/handlers/users';
import { importHandlers } from '@/mocks/handlers/import';
import { settingsHandlers } from '@/mocks/handlers/settings';

export const handlers = [
  ...authHandlers,
  ...dashboardHandlers,
  ...productHandlers,
  ...categoryHandlers,
  ...reviewHandlers,
  ...userHandlers,
  ...importHandlers,
  ...settingsHandlers,
];
