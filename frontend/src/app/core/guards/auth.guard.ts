import { inject } from '@angular/core';
import { Router, type CanActivateFn } from '@angular/router';
import { AuthState } from '../state/auth.state';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthState);
  const router = inject(Router);

  if (auth.isAuthenticated()) {
    return true;
  }
  return router.createUrlTree(['/auth/login']);
};
