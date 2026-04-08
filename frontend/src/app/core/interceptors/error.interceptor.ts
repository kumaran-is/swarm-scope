import { HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    catchError((error) => {
      const message = error?.error?.detail ?? error?.message ?? 'Unknown error';
      console.error(`[HTTP Error] ${req.method} ${req.url}: ${message}`);
      return throwError(() => new Error(message));
    })
  );
};
