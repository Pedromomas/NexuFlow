import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['src/app/core/license-clock.spec.ts', 'src/app/core/license.service.spec.ts', 'src/app/core/access-policy.spec.ts', 'src/app/core/account.service.spec.ts', 'src/app/admin-center.component.spec.ts'],
    setupFiles: ['scripts/vitest-license.setup.ts'],
  },
});
