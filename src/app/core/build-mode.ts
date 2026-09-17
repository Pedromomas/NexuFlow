// Community edition: every local feature is free, without account or license.
// Network diagnostics still need internet; game safety guards remain mandatory.
import { InjectionToken } from '@angular/core';
export const COMMUNITY_EDITION = true;
export const OFFLINE_TEST_EDITION = COMMUNITY_EDITION; // legacy UI compatibility
export const OFFLINE_ACCOUNT_MODE = new InjectionToken<boolean>('offline accounts', {providedIn: 'root', factory: () => OFFLINE_TEST_EDITION});
