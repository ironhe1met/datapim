import { http, HttpResponse, delay } from 'msw';
import type { PaginatedResponse } from '@/types/api';

interface ImportLogEntry {
  id: number;
  filename: string;
  status: 'completed' | 'failed' | 'running';
  started_at: string;
  completed_at: string | null;
  products_created: number;
  products_updated: number;
  errors_count: number;
  error_details: string[] | null;
}

const importLogs: ImportLogEntry[] = [
  {
    id: 1,
    filename: 'TMC.xml',
    status: 'completed',
    started_at: '2026-04-13T09:15:00Z',
    completed_at: '2026-04-13T09:18:32Z',
    products_created: 342,
    products_updated: 1580,
    errors_count: 0,
    error_details: null,
  },
  {
    id: 2,
    filename: 'TMCC.xml',
    status: 'completed',
    started_at: '2026-04-12T14:00:00Z',
    completed_at: '2026-04-12T14:05:11Z',
    products_created: 128,
    products_updated: 945,
    errors_count: 3,
    error_details: [
      'Row 1204: invalid SKU format "ABC--123"',
      'Row 2891: missing required field "name"',
      'Row 3002: duplicate internal_code "IC-99012"',
    ],
  },
  {
    id: 3,
    filename: 'TMC.xml',
    status: 'failed',
    started_at: '2026-04-11T10:30:00Z',
    completed_at: '2026-04-11T10:30:05Z',
    products_created: 0,
    products_updated: 0,
    errors_count: 1,
    error_details: ['Failed to parse XML: unexpected token at line 1'],
  },
  {
    id: 4,
    filename: 'TMCC.xml',
    status: 'completed',
    started_at: '2026-04-10T08:00:00Z',
    completed_at: '2026-04-10T08:04:22Z',
    products_created: 56,
    products_updated: 2104,
    errors_count: 0,
    error_details: null,
  },
  {
    id: 5,
    filename: 'TMC.xml',
    status: 'completed',
    started_at: '2026-04-09T15:45:00Z',
    completed_at: '2026-04-09T15:49:10Z',
    products_created: 210,
    products_updated: 1820,
    errors_count: 5,
    error_details: [
      'Row 445: price value negative "-12.50"',
      'Row 891: unknown category_id "999"',
      'Row 1023: invalid UTF-8 in description',
      'Row 2100: quantity exceeds max (99999)',
      'Row 3500: duplicate SKU "SKU-DUP-001"',
    ],
  },
  {
    id: 6,
    filename: 'TMC.xml',
    status: 'completed',
    started_at: '2026-04-08T11:20:00Z',
    completed_at: '2026-04-08T11:23:45Z',
    products_created: 89,
    products_updated: 1340,
    errors_count: 0,
    error_details: null,
  },
  {
    id: 7,
    filename: 'TMCC.xml',
    status: 'failed',
    started_at: '2026-04-07T09:00:00Z',
    completed_at: '2026-04-07T09:00:02Z',
    products_created: 0,
    products_updated: 0,
    errors_count: 1,
    error_details: ['File not found: inbox/TMCC.xml'],
  },
];

let nextImportId = importLogs.length + 1;

export const importHandlers = [
  http.post('*/api/import/trigger', async () => {
    await delay(2000);

    const newLog: ImportLogEntry = {
      id: nextImportId++,
      filename: 'TMC.xml',
      status: 'completed',
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      products_created: Math.floor(Math.random() * 200) + 50,
      products_updated: Math.floor(Math.random() * 2000) + 500,
      errors_count: 0,
      error_details: null,
    };

    importLogs.unshift(newLog);

    return HttpResponse.json(
      { import_id: newLog.id, status: 'completed' },
      { status: 202 },
    );
  }),

  http.get('*/api/import/logs', async ({ request }) => {
    await delay(300);
    const url = new URL(request.url);
    const page = Math.max(1, Number(url.searchParams.get('page') ?? '1'));
    const perPage = Math.min(
      100,
      Math.max(1, Number(url.searchParams.get('per_page') ?? '10')),
    );

    const total = importLogs.length;
    const lastPage = Math.max(1, Math.ceil(total / perPage));
    const start = (page - 1) * perPage;
    const pageItems = importLogs.slice(start, start + perPage);

    const response: PaginatedResponse<ImportLogEntry> = {
      data: pageItems,
      meta: {
        total,
        page,
        per_page: perPage,
        last_page: lastPage,
      },
    };

    return HttpResponse.json(response);
  }),
];
