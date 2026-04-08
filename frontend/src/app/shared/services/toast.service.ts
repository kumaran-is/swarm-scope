import { Injectable, signal } from '@angular/core';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
}

@Injectable({ providedIn: 'root' })
export class ToastService {
  readonly toasts = signal<Toast[]>([]);

  private show(type: ToastType, message: string): void {
    const id = Math.random().toString(36).slice(2);
    this.toasts.update((list) => [...list.slice(-2), { id, type, message }]);
    setTimeout(() => this.dismiss(id), 5000);
  }

  success(message: string): void { this.show('success', message); }
  error(message: string): void { this.show('error', message); }
  warning(message: string): void { this.show('warning', message); }
  info(message: string): void { this.show('info', message); }

  dismiss(id: string): void {
    this.toasts.update((list) => list.filter((t) => t.id !== id));
  }
}
