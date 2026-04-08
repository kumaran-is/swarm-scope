import { HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    catchError((error) => {
      const detail = error?.error?.detail;
      const message = Array.isArray(detail)
        ? detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join(', ')
        : (detail ?? error?.message ?? 'Unknown error');
      console.error(`[HTTP Error] ${req.method} ${req.url}: ${message}`);
      return throwError(() => new Error(message));
    })
  );
};
