import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthState } from '../state/auth.state';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthState);
  const router = inject(Router);

  const token = auth.accessToken();
  const authedReq = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authedReq).pipe(
    catchError((error) => {
      if (error?.status === 401) {
        auth.clearTokens();
        router.navigate(['/auth/login']);
      }
      return throwError(() => error);
    })
  );
};
